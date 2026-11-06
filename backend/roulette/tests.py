import itertools
import threading
from collections import Counter
from datetime import timedelta
from decimal import Decimal
from fractions import Fraction
from unittest import mock

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.conf import settings
from django.contrib import admin
from django.core.management import CommandError, call_command
from django.db import connection
from django.db.models import Sum
from django.test import RequestFactory, SimpleTestCase, TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken

from accounts.models import User
from base import names
from base.asgi import application
from fairness.rng import first_float, hash_seed, walk_chain
from games.models import Game
from leaderboard.services import weekly_top
from wallet.models import Transaction, Wallet
from wallet.services import InsufficientFunds, open_wallet
from . import bots, engine, feed, runner, services
from .models import (
    RouletteBotBet,
    RouletteBotSettings,
    RouletteChain,
    RouletteRound,
    RouletteSlip,
)

SHORT_CHAIN = mock.patch.object(services, "CHAIN_LENGTH", 200)
ORIGIN = [(b"origin", b"http://localhost:3000")]
RED_BET = [{"bet_type": "red", "amount": "10"}]
# The bets of the design's result screen.
DESIGN_SLIP = [
    {"bet_type": "straight", "value": [17], "amount": "10"},
    {"bet_type": "split", "value": [8, 11], "amount": "5"},
    {"bet_type": "corner", "value": [20, 21, 23, 24], "amount": "5"},
    {"bet_type": "red", "amount": "25"},
    {"bet_type": "dozen", "value": [2], "amount": "5"},
]


def make_player(name):
    user = User.objects.create_user(username=f"{name}@lumora.dev", email=f"{name}@lumora.dev", display_name=name)
    open_wallet(user)
    return user


def ledger_sum(user):
    return Transaction.objects.filter(wallet__user=user).aggregate(total=Sum("amount"))["total"]


def balance(user):
    return Wallet.objects.get(user=user).balance


def spin(result=None):
    """Close the betting of the current round, optionally with a chosen result."""
    current = RouletteRound.objects.first()
    if result is not None:
        RouletteRound.objects.filter(pk=current.pk).update(result=result)
    return services.start_spin(current.pk)


class RouletteEngineTests(SimpleTestCase):
    def valid(self, bet_type, size):
        found = []
        for numbers in itertools.combinations(range(37), size):
            try:
                engine.resolve_bet(bet_type, list(numbers))
            except engine.InvalidBet:
                continue
            found.append(numbers)
        return found

    def test_how_many_inside_bets_the_table_has(self):
        for bet_type, size, count in [
            ("straight", 1, 37),
            ("split", 2, 60),
            ("street", 3, 12),
            ("trio", 3, 2),
            ("corner", 4, 22),
            ("first_four", 4, 1),
        ]:
            with self.subTest(bet_type=bet_type):
                self.assertEqual(len(self.valid(bet_type, size)), count)
        self.assertEqual(len(engine.ALL_BETS["six_line"]), 11)

    def test_multipliers_include_the_stake(self):
        for bet_type, value, multiplier in [
            ("straight", [17], 36),
            ("split", [8, 11], 18),
            ("split", [0, 2], 18),
            ("street", [7, 8, 9], 12),
            ("trio", [0, 1, 2], 12),
            ("corner", [20, 21, 23, 24], 9),
            ("first_four", [0, 1, 2, 3], 9),
            ("six_line", [1, 2, 3, 4, 5, 6], 6),
            ("dozen", [2], 3),
            ("column", [3], 3),
            ("red", [], 2),
            ("high", [], 2),
        ]:
            with self.subTest(bet_type=bet_type, value=value):
                self.assertEqual(engine.resolve_bet(bet_type, value)[1], multiplier)

    def test_splits_follow_the_table(self):
        for numbers in [[8, 11], [11, 8], [8, 9], [0, 1], [0, 3], [33, 36]]:
            with self.subTest(numbers=numbers):
                self.assertEqual(engine.resolve_bet("split", numbers)[1], 18)

    def test_bets_the_table_does_not_have(self):
        for bet_type, value in [
            ("split", [8, 12]),  # not next to each other
            ("split", [3, 4]),  # the end of one street and the start of the next
            ("split", [0, 4]),
            ("split", [8, 8]),
            ("split", [36, 37]),
            ("street", [2, 3, 4]),
            ("street", [0, 1, 2]),  # that one is a trio
            ("trio", [0, 1, 3]),
            ("corner", [2, 3, 5, 6, 7]),
            ("corner", [3, 4, 6, 7]),
            ("first_four", [1, 2, 3, 4]),
            ("six_line", [2, 3, 4, 5, 6, 7]),
            ("six_line", [34, 35, 36, 37, 38, 39]),
            ("straight", [37]),
            ("straight", [-1]),
            ("straight", [True]),
            ("straight", [17.0]),
            ("straight", []),
            ("dozen", [4]),
            ("column", [0]),
            ("red", [1]),
            ("nothing", []),
        ]:
            with self.subTest(bet_type=bet_type, value=value):
                with self.assertRaises(engine.InvalidBet):
                    engine.resolve_bet(bet_type, value)

    def test_every_bet_has_an_exact_rtp_of_36_37(self):
        """Exact RTP: the average payout over all 37 pockets, for every bet on the table."""
        for bet_type, values in engine.ALL_BETS.items():
            for value in values:
                with self.subTest(bet_type=bet_type, value=value):
                    total = sum(engine.payout(bet_type, value, Decimal("1"), p) for p in range(engine.POCKETS))
                    self.assertEqual(Fraction(total) / engine.POCKETS, Fraction(36, 37))

    def test_rtp_simulation_on_a_real_hash_chain(self):
        """200,000 spins of the live game's own chain of seeds, for each kind of bet."""
        rounds = 200_000
        seed = "sim-last-seed"
        hits = Counter()
        for _ in range(rounds):
            seed = hash_seed(seed)
            hits[services.round_result(seed)] += 1
        self.assertEqual(sum(hits.values()), rounds)
        # The spread grows with the multiplier, so a straight gets a wider band.
        for bet_type, value, tolerance in [
            ("red", [], 0.01),
            ("column", [2], 0.015),
            ("six_line", [1, 2, 3, 4, 5, 6], 0.02),
            ("corner", [20, 21, 23, 24], 0.025),
            ("split", [8, 11], 0.035),
            ("straight", [17], 0.05),
        ]:
            with self.subTest(bet_type=bet_type):
                covered, multiplier = engine.resolve_bet(bet_type, value)
                rtp = sum(hits[p] for p in covered) * multiplier / rounds
                self.assertAlmostEqual(rtp, 36 / 37, delta=tolerance, msg=f"RTP of {bet_type} was {rtp:.4f}")

    def test_zero_loses_every_outside_bet(self):
        for bet_type in ["red", "black", "even", "odd", "low", "high"]:
            with self.subTest(bet=bet_type):
                self.assertEqual(engine.payout(bet_type, [], Decimal("10"), 0), 0)

    def test_pocket_range(self):
        self.assertEqual(engine.pocket(0.0), 0)
        self.assertEqual(engine.pocket(0.999999), 36)

    def test_the_wheel_has_every_pocket_once(self):
        self.assertEqual(sorted(engine.WHEEL), list(range(engine.POCKETS)))

    def test_what_a_result_wins_outside(self):
        winning = engine.winning_outside_bets(23)
        self.assertEqual(
            winning,
            [
                {"bet_type": "red", "value": []},
                {"bet_type": "odd", "value": []},
                {"bet_type": "high", "value": []},
                {"bet_type": "dozen", "value": [2]},
                {"bet_type": "column", "value": [2]},
            ],
        )
        self.assertEqual(engine.winning_outside_bets(0), [])
        self.assertEqual([engine.color(n) for n in (0, 23, 24)], ["green", "red", "black"])


@SHORT_CHAIN
class HashChainTests(TestCase):
    def play_rounds(self, count):
        rounds = []
        for _ in range(count):
            current = services.open_round()
            services.start_spin(current.pk)
            rounds.append(services.settle_round(current.pk))
        return rounds

    def test_each_seed_is_the_hash_of_the_next_one(self):
        rounds = self.play_rounds(6)
        for earlier, later in zip(rounds, rounds[1:]):
            self.assertEqual(earlier.seed, hash_seed(later.seed))
            self.assertEqual(later.seed_hash, earlier.seed)

    def test_a_round_can_be_verified_from_what_the_api_shows(self):
        self.play_rounds(4)
        for row in APIClient().get("/api/roulette_rounds").json():
            with self.subTest(number=row["number"]):
                self.assertEqual(hash_seed(row["seed"]), row["seed_hash"])
                self.assertEqual(walk_chain(row["seed"], row["position"] + 1), row["commitment"])
                self.assertEqual(engine.pocket(first_float(row["seed"], "lumora-roulette", 0)), row["result"])
                self.assertEqual(engine.color(row["result"]), row["color"])

    def test_a_finished_chain_is_followed_by_a_new_one(self):
        with mock.patch.object(services, "CHAIN_LENGTH", 3):
            rounds = self.play_rounds(4)
        self.assertEqual(RouletteChain.objects.count(), 2)
        self.assertEqual([r.position for r in rounds], [0, 1, 2, 0])


@SHORT_CHAIN
class RoundCycleTests(TestCase):
    def test_a_whole_cycle(self):
        cycle = runner.Runner()
        RouletteBotSettings.objects.create(is_enabled=False)
        start = timezone.now()

        cycle.step(start)
        current = RouletteRound.objects.get()
        self.assertEqual(current.status, "betting")
        self.assertEqual(current.betting_ends_at, start + timedelta(seconds=18))

        cycle.step(start + timedelta(seconds=17.9))
        current.refresh_from_db()
        self.assertEqual(current.status, "betting")

        spun = start + timedelta(seconds=18)
        cycle.step(spun)
        current.refresh_from_db()
        self.assertEqual((current.status, current.spin_started_at), ("spinning", spun))

        cycle.step(spun + timedelta(seconds=7.9))
        current.refresh_from_db()
        self.assertEqual(current.status, "spinning")

        settled = spun + timedelta(seconds=8)
        cycle.step(settled)
        current.refresh_from_db()
        self.assertEqual((current.status, current.settled_at), ("settled", settled))

        cycle.step(settled + timedelta(seconds=3.9))
        self.assertEqual(RouletteRound.objects.count(), 1)

        cycle.step(settled + timedelta(seconds=4))
        self.assertEqual(RouletteRound.objects.first().number, current.number + 1)

    def test_a_restarted_runner_continues_the_round_it_finds(self):
        user = make_player("a")
        services.open_round()
        services.place_bet(user, "key", RED_BET)
        current = spin(1)

        runner.Runner().step(timezone.now() + timedelta(seconds=9))

        current.refresh_from_db()
        self.assertEqual(current.status, "settled")
        self.assertEqual(balance(user), Decimal("10010.00"))

    def test_a_second_settlement_pays_nothing(self):
        user = make_player("a")
        services.open_round()
        services.place_bet(user, "key", RED_BET)
        current = spin(1)
        services.settle_round(current.pk)
        services.settle_round(current.pk)
        self.assertEqual(Transaction.objects.filter(kind="win").count(), 1)

    def test_events_are_published_only_after_the_commit(self):
        with mock.patch.object(feed, "publish") as publish:
            with self.captureOnCommitCallbacks(execute=True):
                current = services.open_round()
                publish.assert_not_called()
        self.assertEqual(publish.call_args.args[0], "round.betting")
        self.assertEqual(publish.call_args.args[1]["number"], current.number)


@SHORT_CHAIN
class BetTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = make_player("r")
        self.client.force_authenticate(self.user)
        self.round = services.open_round()

    def bet(self, lines=RED_BET, key="key-1"):
        return self.client.post("/api/roulette_bets", {"key": key, "lines": lines})

    def test_one_debit_for_a_whole_slip(self):
        response = self.bet(DESIGN_SLIP)
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body["amount"], body["balance"]), ("50.00", "9950.00"))
        self.assertEqual(body["round"], self.round.number)
        self.assertEqual(body["seat"], f"player-{names.public_id(self.user.pk)}")
        self.assertEqual(len(body["lines"]), 5)
        self.assertEqual(body["lines"][1]["bet_type"], "split")
        self.assertEqual(body["lines"][1]["multiplier"], 18)
        tx = Transaction.objects.get(kind="bet")
        self.assertEqual((tx.amount, tx.game), (Decimal("-50.00"), "lumora-roulette"))
        self.assertEqual(tx.idempotency_key, f"roulette:{self.round.number}:key-1")

    def test_several_slips_in_a_round(self):
        self.assertEqual(self.bet(key="a").status_code, 201)
        self.assertEqual(self.bet(key="b").status_code, 201)
        self.assertEqual(RouletteSlip.objects.count(), 2)
        self.assertEqual(balance(self.user), Decimal("9980.00"))

    def test_a_repeated_key_charges_once(self):
        first = self.bet()
        again = self.bet()
        self.assertEqual((first.status_code, again.status_code), (201, 200))
        self.assertEqual(first.json()["id"], again.json()["id"])
        self.assertEqual(balance(self.user), Decimal("9990.00"))

    def test_a_retry_after_the_round_ended_finds_its_slip(self):
        self.bet()
        spin()
        again = self.bet()
        self.assertEqual(again.status_code, 200)
        self.assertEqual(balance(self.user), Decimal("9990.00"))

    def test_another_player_can_use_the_same_key(self):
        self.bet()
        self.client.force_authenticate(make_player("o"))
        self.assertEqual(self.bet().status_code, 201)

    def test_no_bets_after_the_window_even_before_the_runner_moves(self):
        RouletteRound.objects.update(betting_ends_at=timezone.now() - timedelta(milliseconds=1))
        response = self.bet()
        self.assertEqual((response.status_code, response.json()["code"]), (409, "round_closed"))
        self.assertEqual(balance(self.user), Decimal("10000.00"))

    def test_no_bets_while_spinning_or_after(self):
        spin()
        self.assertEqual(self.bet().json()["code"], "round_closed")
        services.settle_round(self.round.pk)
        self.assertEqual(self.bet(key="b").json()["code"], "round_closed")

    def test_no_round_at_all(self):
        RouletteRound.objects.all().delete()
        self.assertEqual(self.bet().json()["code"], "round_closed")

    def test_bad_lines_are_rejected_and_cost_nothing(self):
        for line, code in [
            ({"bet_type": "split", "value": [8, 12], "amount": "5"}, "invalid_bet"),
            ({"bet_type": "nothing", "amount": "5"}, "invalid_bet"),
            ({"bet_type": "straight", "value": ["a"], "amount": "5"}, "invalid_bet"),
            ({"bet_type": "straight", "value": "17", "amount": "5"}, "invalid_bet"),
            ({"bet_type": "red"}, "invalid_bet"),
            ({"bet_type": "red", "amount": "abc"}, "invalid_bet"),
            ({"bet_type": "red", "amount": "NaN"}, "invalid_bet"),
            ({"bet_type": "red", "amount": "1.005"}, "invalid_bet"),
            ({"bet_type": "red", "amount": "0.99"}, "bet_out_of_range"),
            ({"bet_type": "red", "amount": "-5"}, "bet_out_of_range"),
            ({"bet_type": "red", "amount": "10000.01"}, "bet_out_of_range"),
        ]:
            with self.subTest(line=line):
                response = self.bet([line])
                self.assertEqual((response.status_code, response.json()["code"]), (400, code))
        self.assertEqual(balance(self.user), Decimal("10000.00"))
        self.assertFalse(RouletteSlip.objects.exists())

    def test_a_slip_needs_a_key_and_lines(self):
        for data in [{"lines": RED_BET}, {"key": "a"}, {"key": "a", "lines": []}, {"key": "x" * 37, "lines": RED_BET}]:
            with self.subTest(data=data):
                self.assertEqual(self.client.post("/api/roulette_bets", data).status_code, 400)

    def test_lines_limit_counts_the_whole_round(self):
        thirty = [{"bet_type": "straight", "value": [n], "amount": "1"} for n in range(30)]
        self.assertEqual(self.bet(thirty, "a").status_code, 201)
        twenty_one = [{"bet_type": "split", "value": value, "amount": "1"} for value in engine.ALL_BETS["split"][:21]]
        response = self.bet(twenty_one, "b")
        self.assertEqual((response.status_code, response.json()["code"]), (400, "too_many_lines"))
        self.assertIn("50", response.json()["detail"])
        self.assertEqual(self.bet(twenty_one[:20], "c").status_code, 201)

    def test_total_limit_counts_the_whole_round(self):
        self.assertEqual(self.bet([{"bet_type": "red", "amount": "6000"}], "a").status_code, 201)
        response = self.bet([{"bet_type": "black", "amount": "4000.01"}], "b")
        self.assertEqual((response.status_code, response.json()["code"]), (400, "round_limit_exceeded"))
        self.assertEqual(self.bet([{"bet_type": "black", "amount": "4000"}], "c").status_code, 201)

    def test_not_enough_lc_leaves_no_slip(self):
        Wallet.objects.filter(user=self.user).update(balance=Decimal("5.00"))
        with self.assertRaises(InsufficientFunds):
            services.place_bet(self.user, "key", RED_BET)
        self.assertEqual(self.bet().json()["code"], "not_enough_lc")
        self.assertFalse(RouletteSlip.objects.exists())

    def test_game_switched_off(self):
        Game.objects.filter(slug="lumora-roulette").update(is_active=False)
        self.assertEqual(self.bet().json()["code"], "game_unavailable")

    def test_players_see_only_their_own_slips(self):
        self.bet()
        self.assertEqual(len(self.client.get("/api/roulette_bets").json()), 1)
        self.client.force_authenticate(make_player("o"))
        self.assertEqual(self.client.get("/api/roulette_bets").json(), [])

    def test_needs_a_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.bet().status_code, 401)
        self.assertEqual(self.client.get("/api/roulette_bets/last_round").status_code, 401)

    def test_a_cookie_session_needs_the_csrf_header(self):
        client = APIClient(enforce_csrf_checks=True)
        client.cookies[settings.AUTH_ACCESS_COOKIE] = str(AccessToken.for_user(self.user))
        response = client.post("/api/roulette_bets", {"key": "a", "lines": RED_BET})
        self.assertEqual((response.status_code, response.json()["code"]), (403, "csrf_failed"))


@SHORT_CHAIN
class SettlementTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = make_player("r")
        self.client.force_authenticate(self.user)
        self.round = services.open_round()

    def test_the_designs_example_pays_110(self):
        slip, _ = services.place_bet(self.user, "key", DESIGN_SLIP)
        services.settle_round(spin(23).pk)

        slip.refresh_from_db()
        self.assertEqual(slip.payout, Decimal("110.00"))
        self.assertEqual(
            list(slip.lines.values_list("payout", flat=True)),
            [Decimal("0.00"), Decimal("0.00"), Decimal("45.00"), Decimal("50.00"), Decimal("15.00")],
        )
        self.assertEqual(Transaction.objects.filter(kind="win").count(), 1)
        self.assertEqual(balance(self.user), Decimal("10060.00"))
        self.assertEqual(ledger_sum(self.user), balance(self.user))

    def test_a_losing_slip_gets_no_credit(self):
        services.place_bet(self.user, "key", RED_BET)
        services.settle_round(spin(2).pk)
        self.assertFalse(Transaction.objects.filter(kind="win").exists())
        self.assertEqual(balance(self.user), Decimal("9990.00"))

    def test_every_winning_slip_gets_its_own_credit(self):
        services.place_bet(self.user, "a", RED_BET)
        services.place_bet(self.user, "b", [{"bet_type": "odd", "amount": "20"}])
        services.place_bet(self.user, "c", [{"bet_type": "black", "amount": "30"}])
        services.settle_round(spin(1).pk)
        wins = Transaction.objects.filter(kind="win").order_by("amount")
        self.assertEqual([tx.amount for tx in wins], [Decimal("20.00"), Decimal("40.00")])
        self.assertEqual(ledger_sum(self.user), balance(self.user))

    def test_ledger_equals_balance_over_many_rounds(self):
        for number in range(5):
            services.place_bet(self.user, f"key-{number}", DESIGN_SLIP)
            services.settle_round(spin().pk)
            services.open_round()
        self.assertEqual(ledger_sum(self.user), balance(self.user))
        paid = RouletteSlip.objects.aggregate(total=Sum("payout"))["total"] or Decimal("0.00")
        self.assertEqual(balance(self.user), Decimal("10000.00") - 5 * 50 + paid)

    def test_rebet_gets_the_last_settled_round(self):
        self.assertEqual(self.client.get("/api/roulette_bets/last_round").json(), {"round": None, "lines": []})
        services.place_bet(self.user, "a", DESIGN_SLIP[:2])
        services.place_bet(self.user, "b", DESIGN_SLIP[3:4])
        services.settle_round(spin(23).pk)
        settled = self.round.number

        services.open_round()
        services.place_bet(self.user, "c", RED_BET)  # the open round doesn't count yet

        body = self.client.get("/api/roulette_bets/last_round").json()
        self.assertEqual(body["round"], settled)
        self.assertEqual([line["bet_type"] for line in body["lines"]], ["straight", "split", "red"])
        self.assertEqual(body["lines"][2]["amount"], "25.00")

    def test_a_broken_feed_does_not_lose_the_bet(self):
        with mock.patch("base.live.get_channel_layer", side_effect=ConnectionError):
            with self.assertLogs("base.live", "ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    services.place_bet(self.user, "key", RED_BET)
        self.assertEqual(RouletteSlip.objects.count(), 1)

    def test_the_settled_event_says_who_won_how_much(self):
        services.place_bet(self.user, "a", RED_BET)
        services.place_bet(self.user, "b", [{"bet_type": "black", "amount": "5"}])
        RouletteBotBet.objects.create(
            round=self.round, name="kite", amount="50", lines=[{"bet_type": "odd", "value": [], "amount": "50"}]
        )
        current = spin(1)
        with mock.patch.object(feed, "publish") as publish:
            with self.captureOnCommitCallbacks(execute=True):
                services.settle_round(current.pk)
        event, data = publish.call_args.args
        self.assertEqual(event, "round.settled")
        self.assertEqual(data["seed"], current.seed)
        self.assertEqual(
            [(row["player"], row["is_bot"], row["amount"], row["payout"]) for row in data["payouts"]],
            [("r", False, "15.00", "20.00"), ("kite", True, "50.00", "100.00")],
        )


@SHORT_CHAIN
class BotTests(TestCase):
    def setUp(self):
        self.config = RouletteBotSettings.load()
        self.round = services.open_round()

    def add_bots(self):
        for planned in bots.plan_round(self.round.betting_ends_at):
            bots.place(self.round.pk, planned)

    def test_the_admin_settings_decide_the_bets(self):
        RouletteBotSettings.objects.update(count=5, min_bet="20.00", max_bet="30.00")
        self.add_bots()
        rows = RouletteBotBet.objects.all()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len({row.name for row in rows}), 5)
        for row in rows:
            self.assertTrue(Decimal("20") <= row.amount <= Decimal("30"))

    def test_bots_place_real_bets_that_add_up(self):
        for _ in range(30):
            RouletteBotBet.objects.all().delete()
            self.add_bots()
            for row in RouletteBotBet.objects.all():
                self.assertEqual(sum(Decimal(line["amount"]) for line in row.lines), row.amount)
                for line in row.lines:
                    engine.resolve_bet(line["bet_type"], line["value"])

    def test_switched_off(self):
        RouletteBotSettings.objects.update(is_enabled=False)
        self.assertEqual(bots.plan_round(self.round.betting_ends_at), [])

    def test_bets_come_inside_the_betting_window(self):
        start = self.round.betting_ends_at - timedelta(seconds=engine.BETTING_SECONDS)
        for planned in bots.plan_round(self.round.betting_ends_at):
            self.assertTrue(start <= planned.at < self.round.betting_ends_at)

    def test_no_bot_joins_a_spinning_round(self):
        spin()
        planned = bots.PlannedBet(timezone.now(), "late", Decimal("10.00"), RED_BET)
        self.assertIsNone(bots.place(self.round.pk, planned))

    def test_runner_places_them_when_they_are_due(self):
        line = [{"bet_type": "red", "value": [], "amount": "10.00"}]
        cycle = runner.Runner()
        cycle.planned_bots = [
            bots.PlannedBet(timezone.now(), "now", Decimal("10.00"), line),
            bots.PlannedBet(timezone.now() + timedelta(seconds=3), "later", Decimal("10.00"), line),
        ]
        cycle.step()
        self.assertEqual([bot.name for bot in RouletteBotBet.objects.all()], ["now"])

    def test_bots_win_and_lose_without_touching_a_wallet(self):
        player = make_player("r")
        before = Transaction.objects.count()
        RouletteBotBet.objects.create(
            round=self.round, name="w", amount="100", lines=[{"bet_type": "red", "value": [], "amount": "100"}]
        )
        RouletteBotBet.objects.create(
            round=self.round, name="l", amount="100", lines=[{"bet_type": "black", "value": [], "amount": "100"}]
        )
        services.settle_round(spin(1).pk)

        winner, loser = RouletteBotBet.objects.order_by("id")
        self.assertEqual((winner.payout, loser.payout), (Decimal("200.00"), Decimal("0.00")))
        self.assertEqual(Transaction.objects.count(), before)
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(balance(player), Decimal("10000.00"))
        self.assertEqual(weekly_top(), [])

    def test_only_the_current_rounds_bots_are_kept(self):
        self.add_bots()
        services.settle_round(spin().pk)
        self.assertTrue(RouletteBotBet.objects.exists())  # the settled table stays on screen
        services.open_round()
        self.assertFalse(RouletteBotBet.objects.exists())


@SHORT_CHAIN
class SecretsTests(TestCase):
    """Nothing public may show the result before the spin, or the seed before the settlement."""

    client_class = APIClient

    def setUp(self):
        self.round = services.open_round()

    def test_betting_hides_the_result_and_the_seed(self):
        data = feed.snapshot()["round"]
        for key in ["result", "color", "seed", "winning"]:
            self.assertNotIn(key, data)
        self.assertEqual(data["seed_hash"], self.round.seed_hash)

    def test_spinning_shows_the_result_but_not_the_seed(self):
        current = spin(23)
        data = feed.snapshot()["round"]
        self.assertEqual((data["result"], data["color"]), (23, "red"))
        self.assertNotIn("seed", data)
        self.assertEqual(data["spin_ends_at"], (current.spin_started_at + timedelta(seconds=8)).isoformat())

    def test_settled_shows_the_seed(self):
        services.settle_round(spin(23).pk)
        data = feed.snapshot()
        self.assertEqual(data["round"]["seed"], self.round.seed)
        self.assertEqual(data["round"]["winning"][0], {"bet_type": "red", "value": []})
        self.assertEqual(data["history"], [{"number": self.round.number, "result": 23, "color": "red"}])

    def test_history_keeps_the_last_14(self):
        for _ in range(16):
            services.start_spin(self.round.pk)
            services.settle_round(self.round.pk)
            self.round = services.open_round()
        history = feed.snapshot()["history"]
        self.assertEqual(len(history), 14)
        self.assertEqual(history[0]["number"], self.round.number - 1)

    def test_rounds_api_shows_only_settled_rounds(self):
        self.assertEqual(self.client.get("/api/roulette_rounds").json(), [])
        self.assertEqual(self.client.get(f"/api/roulette_rounds/{self.round.number}").status_code, 404)
        current = spin()
        self.assertEqual(self.client.get("/api/roulette_rounds").json(), [])

        services.settle_round(current.pk)
        row = self.client.get(f"/api/roulette_rounds/{self.round.number}").json()
        self.assertEqual(row["seed"], self.round.seed)

    def test_admin_hides_a_live_rounds_secrets_and_the_chains_last_seed(self):
        self.client.force_login(User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev"))
        for url in [
            f"/admin/roulette/rouletteround/{self.round.pk}/change/",
            "/admin/roulette/rouletteround/",
            f"/admin/roulette/roulettechain/{self.round.chain_id}/change/",
        ]:
            with self.subTest(url=url):
                page = self.client.get(url).content.decode()
                self.assertNotIn(self.round.seed, page)
                self.assertNotIn(self.round.chain.last_seed, page)

    def test_money_and_history_are_read_only_in_the_admin(self):
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev")
        for model in [RouletteChain, RouletteRound, RouletteSlip]:
            with self.subTest(model=model.__name__):
                self.assertFalse(admin.site._registry[model].has_add_permission(request))
                self.assertFalse(admin.site._registry[model].has_change_permission(request))


def in_a_new_connection(func):
    results = []

    def worker():
        try:
            results.append(func())
        except Exception as exc:
            results.append(exc)
        finally:
            connection.close()

    thread = threading.Thread(target=worker)
    thread.start()
    thread.join()
    return results[0]


class RunnerLockTests(TransactionTestCase):
    def setUp(self):
        self.addCleanup(self.release)

    def release(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock_all()")

    def test_only_one_runner_gets_the_lock(self):
        self.assertTrue(runner.acquire_lock())
        self.assertFalse(in_a_new_connection(runner.acquire_lock))

    def test_a_second_run_roulette_refuses_to_start(self):
        runner.acquire_lock()
        result = in_a_new_connection(lambda: call_command("run_roulette"))
        self.assertIsInstance(result, CommandError)

    def test_crash_and_roulette_have_their_own_locks(self):
        from crash.runner import acquire_lock as acquire_crash_lock

        self.assertTrue(runner.acquire_lock())
        self.assertTrue(in_a_new_connection(acquire_crash_lock))


class ParallelRequestTests(TransactionTestCase):
    """Real parallel requests on PostgreSQL: the round's row lock decides who was first."""

    def setUp(self):
        Game.objects.get_or_create(
            slug="lumora-roulette",
            defaults={"title": "Lumora Roulette", "category": "table", "rtp": Decimal("97.30"), "is_active": True},
        )
        patch = mock.patch.object(services, "CHAIN_LENGTH", 200)
        patch.start()
        self.addCleanup(patch.stop)
        self.round = services.open_round()

    def run_in_threads(self, funcs):
        barrier = threading.Barrier(len(funcs))
        results = [None] * len(funcs)

        def worker(index, func):
            try:
                barrier.wait()
                results[index] = func()
            except Exception as exc:
                results[index] = exc
            finally:
                connection.close()

        threads = [threading.Thread(target=worker, args=item) for item in enumerate(funcs)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_parallel_retries_with_one_key_charge_once(self):
        player = make_player("retry")
        results = self.run_in_threads([lambda: services.place_bet(player, "same", RED_BET)] * 8)
        self.assertTrue(all(isinstance(result, tuple) for result in results), results)
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(balance(player), Decimal("9990.00"))
        self.assertEqual(ledger_sum(player), balance(player))

    def test_parallel_slips_cannot_pass_the_round_limit(self):
        player = make_player("limit")
        lines = [{"bet_type": "red", "amount": "4000"}]
        results = self.run_in_threads([lambda n=n: services.place_bet(player, f"k{n}", lines) for n in range(5)])
        self.assertEqual(sum(isinstance(result, tuple) for result in results), 2)
        self.assertEqual(balance(player), Decimal("2000.00"))

    def test_a_bet_at_the_last_moment_is_in_or_out_never_lost_in_between(self):
        players = [make_player(f"p{n}") for n in range(8)]
        funcs = [lambda player=player: services.place_bet(player, "key", RED_BET) for player in players]
        funcs.insert(4, lambda: services.start_spin(self.round.pk))
        results = self.run_in_threads(funcs)
        services.settle_round(self.round.pk)

        placed = [result for result in results if isinstance(result, tuple)]
        refused = [result for result in results if isinstance(result, services.RoundConflict)]
        self.assertEqual(len(placed) + len(refused), 8)
        self.assertEqual(RouletteSlip.objects.count(), len(placed))
        self.assertEqual(Transaction.objects.filter(kind="bet").count(), len(placed))
        for player in players:
            self.assertEqual(ledger_sum(player), balance(player))


class WebSocketTests(TransactionTestCase):
    """The sockets read rows from another thread, so the data must really be committed."""

    def setUp(self):
        Game.objects.get_or_create(
            slug="lumora-roulette",
            defaults={"title": "Lumora Roulette", "category": "table", "rtp": Decimal("97.30"), "is_active": True},
        )
        patch = mock.patch.object(services, "CHAIN_LENGTH", 200)
        patch.start()
        self.addCleanup(patch.stop)

    async def connect(self, headers=ORIGIN):
        socket = WebsocketCommunicator(application, "/ws/roulette", headers=headers)
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        return socket

    async def test_a_round_goes_out_live(self):
        user = await database_sync_to_async(make_player)("live")
        current = await database_sync_to_async(services.open_round)()
        socket = await self.connect()

        snapshot = await socket.receive_json_from()
        self.assertEqual(snapshot["type"], "snapshot")
        self.assertEqual(snapshot["round"]["status"], "betting")
        self.assertNotIn("result", snapshot["round"])

        await database_sync_to_async(services.place_bet)(user, "key", DESIGN_SLIP)
        placed = await socket.receive_json_from()
        self.assertEqual(placed["type"], "bet.placed")
        self.assertEqual((placed["player"], placed["is_bot"], placed["amount"]), ("live", False, "50.00"))
        self.assertEqual(placed["seat"], f"player-{names.public_id(user.pk)}")
        self.assertEqual(placed["lines"][1], {"bet_type": "split", "value": [8, 11], "amount": "5.00"})

        await database_sync_to_async(spin)(23)
        spinning = await socket.receive_json_from()
        self.assertEqual((spinning["type"], spinning["result"], spinning["color"]), ("round.spinning", 23, "red"))
        self.assertNotIn("seed", spinning)

        await database_sync_to_async(services.settle_round)(current.pk)
        settled = await socket.receive_json_from()
        self.assertEqual(settled["type"], "round.settled")
        self.assertEqual(settled["seed"], current.seed)
        self.assertEqual(settled["payouts"][0]["payout"], "110.00")
        await socket.disconnect()

        socket = await self.connect()
        snapshot = await socket.receive_json_from()
        self.assertEqual(snapshot["bets"][0]["payout"], "110.00")
        self.assertEqual(snapshot["history"], [{"number": current.number, "result": 23, "color": "red"}])
        await socket.disconnect()

    async def test_bots_are_marked_in_the_feed(self):
        current = await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        await socket.receive_json_from()

        lines = [{"bet_type": "red", "value": [], "amount": "50.00"}]
        planned = bots.PlannedBet(timezone.now(), "kite", Decimal("50.00"), lines)
        await database_sync_to_async(bots.place)(current.pk, planned)

        message = await socket.receive_json_from()
        self.assertEqual((message["player"], message["is_bot"], message["lines"]), ("kite", True, lines))
        await socket.disconnect()

    async def test_clients_can_only_listen(self):
        await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        await socket.receive_json_from()
        await socket.send_to(text_data="not json at all")
        await socket.send_json_to({"type": "bet.placed", "amount": "1"})
        self.assertTrue(await socket.receive_nothing())
        self.assertFalse(await database_sync_to_async(RouletteSlip.objects.exists)())
        await socket.disconnect()

    async def test_another_site_cannot_open_the_socket(self):
        socket = WebsocketCommunicator(application, "/ws/roulette", headers=[(b"origin", b"https://evil.example")])
        connected, _ = await socket.connect()
        self.assertFalse(connected)
        await socket.disconnect()


class SeatPrivacyTests(TestCase):
    """A seat identifies a player to the other players: never by the sequential user id or the email."""

    def setUp(self):
        self.user = User.objects.create_user(username="seat.owner@lumora.dev", email="seat.owner@lumora.dev")
        open_wallet(self.user)

    def test_the_seat_is_a_keyed_hash_and_matches_my_public_id(self):
        seat = feed.slip_seat(self.user.pk)
        self.assertEqual(seat, f"player-{names.public_id(self.user.pk)}")
        self.assertNotEqual(seat, f"player-{self.user.pk}")
        api = APIClient()
        api.force_authenticate(self.user)
        me = api.get("/api/me").json()
        self.assertEqual(f"player-{me['public_id']}", seat)  # what the page uses as "my seat"

    def test_a_player_without_a_display_name_has_no_email_in_the_table(self):
        current = services.open_round()
        slip, _ = services.place_bet(self.user, "k1", DESIGN_SLIP)  # (the slip, created)
        data = feed.slip_data(RouletteSlip.objects.select_related("user", "round").get(pk=slip.pk))
        self.assertRegex(data["player"], r"^Player [0-9a-f]{6}$")
        shown = str(data)
        self.assertNotIn("seat.owner", shown)
        self.assertNotIn(f"player-{self.user.pk}'", shown)
        self.assertEqual(data["round"], current.number)
