import json
import threading
from datetime import timedelta
from decimal import Decimal
from unittest import mock

from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from channels_redis.core import RedisChannelLayer
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
from base import live
from base.asgi import application
from fairness.rng import first_float, hash_seed, walk_chain
from games.models import Game
from leaderboard.services import weekly_top
from wallet.models import Transaction, Wallet
from wallet.services import InsufficientFunds, open_wallet
from . import bots, engine, feed, runner, services
from .models import CrashBotBet, CrashBotSettings, CrashChain, CrashRound, RoundBet

SHORT_CHAIN = mock.patch.object(services, "CHAIN_LENGTH", 200)
ORIGIN = [(b"origin", b"http://localhost:3000")]


def make_player(name):
    user = User.objects.create_user(username=f"{name}@lumora.dev", email=f"{name}@lumora.dev", display_name=name)
    open_wallet(user)
    return user


def ledger_sum(user):
    return Transaction.objects.filter(wallet__user=user).aggregate(total=Sum("amount"))["total"]


def balance(user):
    return Wallet.objects.get(user=user).balance


def fly(crash_point="5.00", seconds_ago=10):
    """Put the current betting round in the air, as if it took off some seconds ago."""
    current = CrashRound.objects.first()
    started_at = timezone.now() - timedelta(seconds=seconds_ago)
    CrashRound.objects.filter(pk=current.pk).update(crash_point=crash_point)
    return services.start_flight(current.pk, started_at)


class CrashEngineTests(SimpleTestCase):
    def test_crash_point(self):
        self.assertEqual(engine.crash_point(0.0), Decimal("1.00"))  # 0.97 is raised to the minimum
        self.assertEqual(engine.crash_point(0.5), Decimal("1.94"))
        self.assertEqual(engine.crash_point(0.75), Decimal("3.88"))
        self.assertEqual(str(engine.crash_point(0.1182)), "1.10")  # always two decimals, as in the API
        with self.assertRaises(ValueError):
            engine.crash_point(1.0)

    def test_crash_point_never_goes_above_the_highest_target(self):
        self.assertEqual(engine.crash_point(1 - 2**-52), engine.MAX_TARGET)

    def test_payout(self):
        self.assertEqual(engine.payout(Decimal("100"), Decimal("2.00"), Decimal("2.00")), Decimal("200.00"))
        self.assertEqual(engine.payout(Decimal("100"), Decimal("2.00"), Decimal("1.99")), Decimal("0.00"))

    def test_multiplier_is_a_function_of_time(self):
        self.assertEqual(str(engine.multiplier_at(0)), "1.00")
        self.assertEqual(engine.multiplier_at(-50), Decimal("1.00"))
        self.assertEqual(engine.multiplier_at(1000), Decimal("1.06"))  # e^0.06 = 1.0618
        self.assertEqual(engine.multiplier_at(11_552), Decimal("1.99"))  # just under ln(2) / 0.06
        self.assertEqual(engine.multiplier_at(11_553), Decimal("2.00"))
        self.assertEqual(engine.multiplier_at(38_377), Decimal("10.00"))
        self.assertEqual(engine.multiplier_at(10_000_000), engine.MAX_TARGET)

    def test_multiplier_never_goes_down(self):
        values = [engine.multiplier_at(ms) for ms in range(0, 60_000, 50)]
        self.assertEqual(values, sorted(values))

    def test_rtp_simulation_is_about_97_percent(self):
        """Monte Carlo over 200,000 provably fair rounds, the same check Zeus Legacy will get."""
        self.assert_rtp([engine.crash_point(first_float("sim-seed", "sim-client", n)) for n in range(200_000)])

    def test_rtp_simulation_on_a_real_hash_chain(self):
        """The same check on 200,000 rounds of the live game's own chain of seeds."""
        seed = "sim-last-seed"
        points = []
        for _ in range(200_000):
            seed = hash_seed(seed)
            points.append(services.round_result(seed))
        self.assert_rtp(points)

    def assert_rtp(self, points):
        # The spread grows with the target, so 10x gets a wider band.
        for target, tolerance in [("1.50", 0.01), ("2.00", 0.01), ("10.00", 0.04)]:
            with self.subTest(target=target):
                target = Decimal(target)
                returned = sum(engine.payout(Decimal("1"), target, point) for point in points)
                rtp = float(returned) / len(points)
                self.assertAlmostEqual(rtp, 0.97, delta=tolerance, msg=f"RTP at {target}x was {rtp:.4f}")


@SHORT_CHAIN
class HashChainTests(TestCase):
    def play_rounds(self, count):
        rounds = []
        for _ in range(count):
            current = services.open_round()
            services.start_flight(current.pk)
            rounds.append(services.crash_round(current.pk))
        return rounds

    def test_each_seed_is_the_hash_of_the_next_one(self):
        rounds = self.play_rounds(6)
        for earlier, later in zip(rounds, rounds[1:]):
            self.assertEqual(earlier.seed, hash_seed(later.seed))
            self.assertEqual(later.seed_hash, earlier.seed)  # the commitment was public a round before

    def test_every_round_can_be_verified_from_what_the_api_shows(self):
        self.play_rounds(4)
        client = APIClient()
        for row in client.get("/api/crash_rounds").json():
            with self.subTest(number=row["number"]):
                self.assertEqual(hash_seed(row["seed"]), row["seed_hash"])
                self.assertEqual(walk_chain(row["seed"], row["position"] + 1), row["commitment"])
                self.assertEqual(str(engine.crash_point(first_float(row["seed"], "neon-crash", 0))), row["crash_point"])

    def test_a_finished_chain_is_followed_by_a_new_one(self):
        with mock.patch.object(services, "CHAIN_LENGTH", 3):
            rounds = self.play_rounds(4)
        self.assertEqual(CrashChain.objects.count(), 2)
        self.assertEqual([r.position for r in rounds], [0, 1, 2, 0])
        self.assertEqual([r.number for r in rounds], [1, 2, 3, 4])


@SHORT_CHAIN
class RoundCycleTests(TestCase):
    def test_a_whole_cycle(self):
        cycle = runner.Runner()
        CrashBotSettings.objects.create(is_enabled=False)
        start = timezone.now()

        cycle.step(start)
        current = CrashRound.objects.get()
        self.assertEqual(current.status, "betting")
        self.assertEqual(current.betting_ends_at, start + timedelta(seconds=7))

        cycle.step(start + timedelta(seconds=6.9))
        current.refresh_from_db()
        self.assertEqual(current.status, "betting")

        took_off = start + timedelta(seconds=7)
        cycle.step(took_off)
        CrashRound.objects.update(crash_point="1.50")
        current.refresh_from_db()
        self.assertEqual((current.status, current.started_at), ("flying", took_off))

        crash_time = took_off + timedelta(milliseconds=6758)  # 1.50x
        cycle.step(crash_time - timedelta(milliseconds=50))
        current.refresh_from_db()
        self.assertEqual(current.status, "flying")

        cycle.step(crash_time)
        current.refresh_from_db()
        self.assertEqual((current.status, current.crashed_at), ("crashed", crash_time))

        cycle.step(crash_time + timedelta(seconds=2.9))
        self.assertEqual(CrashRound.objects.count(), 1)

        cycle.step(crash_time + timedelta(seconds=3))
        self.assertEqual(CrashRound.objects.first().number, current.number + 1)

    def test_a_restarted_runner_ends_a_flight_it_missed(self):
        user = make_player("a")
        services.open_round()
        services.place_bet(user, "100", "2.00")
        current = fly("3.00", seconds_ago=60)

        runner.Runner().step()

        current.refresh_from_db()
        self.assertEqual(current.status, "crashed")
        self.assertEqual(RoundBet.objects.get().payout, Decimal("200.00"))

    def test_events_are_published_only_after_the_commit(self):
        with mock.patch.object(feed, "publish") as publish:
            with self.captureOnCommitCallbacks(execute=True):
                current = services.open_round()
                publish.assert_not_called()
        publish.assert_called_once()
        self.assertEqual(publish.call_args.args[0], "round.betting")
        self.assertEqual(publish.call_args.args[1]["number"], current.number)


@SHORT_CHAIN
class BetTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = make_player("c")
        self.client.force_authenticate(self.user)
        self.round = services.open_round()

    def bet(self, amount="100", target=None):
        data = {"amount": amount} | ({"target": target} if target else {})
        return self.client.post("/api/crash_bets", data)

    def test_bet_takes_the_coins_at_once(self):
        response = self.bet("100", "2.00")
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertEqual((body["status"], body["target"], body["balance"]), ("active", "2.00", "9900.00"))
        self.assertEqual(body["round"], self.round.number)
        tx = Transaction.objects.get(kind="bet")
        self.assertEqual((tx.amount, tx.game), (Decimal("-100.00"), "neon-crash"))
        self.assertEqual(tx.idempotency_key, f"crash:{self.round.number}:bet")

    def test_target_is_optional(self):
        self.assertIsNone(self.bet().json()["target"])

    def test_no_bets_after_the_window_even_before_the_runner_moves(self):
        CrashRound.objects.update(betting_ends_at=timezone.now() - timedelta(milliseconds=1))
        response = self.bet()
        self.assertEqual((response.status_code, response.json()["code"]), (409, "round_closed"))
        self.assertEqual(balance(self.user), Decimal("10000.00"))

    def test_no_bets_in_flight_or_after_the_crash(self):
        fly()
        self.assertEqual(self.bet().json()["code"], "round_closed")
        services.crash_round(self.round.pk)
        self.assertEqual(self.bet().json()["code"], "round_closed")

    def test_no_round_at_all(self):
        CrashRound.objects.all().delete()
        self.assertEqual(self.bet().json()["code"], "round_closed")

    def test_one_bet_per_round(self):
        self.bet()
        response = self.bet()
        self.assertEqual((response.status_code, response.json()["code"]), (409, "already_bet"))
        self.assertEqual(balance(self.user), Decimal("9900.00"))

    def test_bad_bets_are_rejected_and_cost_nothing(self):
        for amount, target in [("0.50", "2"), ("10", "1.00"), ("999999", "2"), ("abc", "2"), ("10", "1.505")]:
            with self.subTest(amount=amount, target=target):
                self.assertEqual(self.bet(amount, target).status_code, 400)
        self.assertEqual(balance(self.user), Decimal("10000.00"))
        self.assertFalse(RoundBet.objects.exists())

    def test_not_enough_lc_leaves_no_bet(self):
        Wallet.objects.filter(user=self.user).update(balance=Decimal("5.00"))
        with self.assertRaises(InsufficientFunds):
            services.place_bet(self.user, "10")
        self.assertFalse(RoundBet.objects.exists())

    def test_game_switched_off(self):
        Game.objects.filter(slug="neon-crash").update(is_active=False)
        self.assertEqual(self.bet().json()["code"], "game_unavailable")

    def test_players_see_only_their_own_bets(self):
        self.bet()
        self.assertEqual(len(self.client.get("/api/crash_bets").json()), 1)
        self.client.force_authenticate(make_player("o"))
        self.assertEqual(self.client.get("/api/crash_bets").json(), [])

    def test_needs_a_login(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.bet().status_code, 401)
        self.assertEqual(self.client.post("/api/crash_bets/cash_out").status_code, 401)

    def test_a_cookie_session_needs_the_csrf_header(self):
        client = APIClient(enforce_csrf_checks=True)
        client.cookies[settings.AUTH_ACCESS_COOKIE] = str(AccessToken.for_user(self.user))
        response = client.post("/api/crash_bets", {"amount": "100"})
        self.assertEqual((response.status_code, response.json()["code"]), (403, "csrf_failed"))
        self.assertFalse(RoundBet.objects.exists())


@SHORT_CHAIN
class CashOutTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = make_player("c")
        self.client.force_authenticate(self.user)
        self.round = services.open_round()

    def assert_ledger_matches(self):
        self.assertEqual(ledger_sum(self.user), balance(self.user))

    def test_manual_cash_out_pays_the_servers_multiplier(self):
        services.place_bet(self.user, "100")
        current = fly("5.00", seconds_ago=10)
        now = current.started_at + timedelta(seconds=10)

        bet = services.cash_out(self.user, now)

        self.assertEqual((bet.status, bet.multiplier, bet.payout), ("cashed_out", Decimal("1.82"), Decimal("182.00")))
        self.assertEqual(balance(self.user), Decimal("10082.00"))
        self.assert_ledger_matches()

    def test_cash_out_through_the_api(self):
        services.place_bet(self.user, "100")
        fly("5.00", seconds_ago=10)
        response = self.client.post("/api/crash_bets/cash_out")
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(body["status"], "cashed_out")
        self.assertEqual(Decimal(body["balance"]), Decimal("9900.00") + Decimal(body["payout"]))

    def test_cash_out_after_the_crash_point_is_too_late_before_the_crash_event(self):
        services.place_bet(self.user, "100")
        current = fly("1.50", seconds_ago=60)

        with self.assertRaises(services.RoundConflict) as caught:
            services.cash_out(self.user, current.started_at + timedelta(seconds=60))

        self.assertEqual(caught.exception.code, "too_late")
        current.refresh_from_db()
        self.assertEqual(current.status, "flying")  # the crash really hasn't been sent yet
        self.assertEqual(balance(self.user), Decimal("9900.00"))

    def test_at_the_exact_crash_point_is_too_late(self):
        services.place_bet(self.user, "100")
        current = fly("2.00")
        with self.assertRaises(services.RoundConflict):
            services.cash_out(self.user, current.started_at + timedelta(milliseconds=11_553))
        bet = services.cash_out(self.user, current.started_at + timedelta(milliseconds=11_552))
        self.assertEqual(bet.multiplier, Decimal("1.99"))

    def test_a_1x_round_can_never_be_cashed_out(self):
        services.place_bet(self.user, "100")
        current = fly("1.00", seconds_ago=0)
        with self.assertRaises(services.RoundConflict):
            services.cash_out(self.user, current.started_at)

    def test_cash_out_after_the_crash(self):
        services.place_bet(self.user, "100")
        fly("1.50", seconds_ago=60)
        services.crash_round(self.round.pk)
        response = self.client.post("/api/crash_bets/cash_out")
        self.assertEqual((response.status_code, response.json()["code"]), (409, "too_late"))
        self.assertEqual(RoundBet.objects.get().status, "lost")

    def test_cash_out_before_the_flight(self):
        services.place_bet(self.user, "100")
        self.assertEqual(self.client.post("/api/crash_bets/cash_out").json()["code"], "not_flying")

    def test_cash_out_without_a_bet(self):
        fly()
        self.assertEqual(self.client.post("/api/crash_bets/cash_out").json()["code"], "no_bet")

    def test_second_cash_out_pays_nothing(self):
        services.place_bet(self.user, "100")
        fly()
        services.cash_out(self.user)
        paid = balance(self.user)
        response = self.client.post("/api/crash_bets/cash_out")
        self.assertEqual(response.json()["code"], "already_cashed_out")
        self.assertEqual(balance(self.user), paid)

    def test_auto_cash_out_pays_exactly_at_the_target(self):
        services.place_bet(self.user, "100", "1.50")
        current = fly("5.00", seconds_ago=30)  # far past the target already

        services.pay_auto_cash_outs(current.pk)

        bet = RoundBet.objects.get()
        self.assertEqual((bet.status, bet.multiplier, bet.payout), ("cashed_out", Decimal("1.50"), Decimal("150.00")))
        self.assert_ledger_matches()

    def test_auto_cash_out_waits_for_its_target(self):
        services.place_bet(self.user, "100", "3.00")
        current = fly("5.00", seconds_ago=1)
        services.pay_auto_cash_outs(current.pk)
        self.assertEqual(RoundBet.objects.get().status, "active")

    def test_the_crash_pays_a_target_the_runner_did_not_reach_in_time(self):
        services.place_bet(self.user, "100", "2.00")
        current = fly("2.00", seconds_ago=60)
        services.crash_round(current.pk)
        self.assertEqual(RoundBet.objects.get().payout, Decimal("200.00"))

    def test_the_crash_loses_a_target_above_the_crash_point(self):
        services.place_bet(self.user, "100", "2.01")
        current = fly("2.00", seconds_ago=60)
        services.crash_round(current.pk)
        bet = RoundBet.objects.get()
        self.assertEqual((bet.status, bet.payout), ("lost", Decimal("0.00")))
        self.assertEqual(balance(self.user), Decimal("9900.00"))

    def test_manual_click_after_a_passed_target_pays_the_target(self):
        services.place_bet(self.user, "100", "1.50")
        current = fly("5.00", seconds_ago=20)
        bet = services.cash_out(self.user, current.started_at + timedelta(seconds=20))
        self.assertEqual((bet.multiplier, bet.payout), (Decimal("1.50"), Decimal("150.00")))

    def test_a_click_after_the_crash_point_still_gets_a_target_it_reached(self):
        services.place_bet(self.user, "100", "2.00")
        current = fly("2.00", seconds_ago=60)
        bet = services.cash_out(self.user, current.started_at + timedelta(seconds=60))
        self.assertEqual(bet.multiplier, Decimal("2.00"))

    def test_crash_can_run_twice_and_pays_once(self):
        services.place_bet(self.user, "100", "2.00")
        current = fly("3.00", seconds_ago=60)
        services.crash_round(current.pk)
        services.crash_round(current.pk)
        self.assertEqual(Transaction.objects.filter(kind="win").count(), 1)

    def test_ledger_equals_balance_over_many_rounds(self):
        user = self.user
        for number, target in enumerate(["1.50", None, "9.00", None, "1.10"]):
            current = CrashRound.objects.first()
            services.place_bet(user, "100", target)
            fly("2.00", seconds_ago=5)
            if target is None and number == 1:
                services.cash_out(user)
            services.crash_round(current.pk)
            services.open_round()
        self.assert_ledger_matches()
        wins = RoundBet.objects.aggregate(total=Sum("payout"))["total"]
        self.assertEqual(balance(user), Decimal("10000.00") - 5 * 100 + wins)

    def test_a_broken_feed_does_not_lose_the_bet(self):
        with mock.patch.object(live, "get_channel_layer", side_effect=ConnectionError):
            with self.assertLogs("base.live", "ERROR"):
                with self.captureOnCommitCallbacks(execute=True):
                    services.place_bet(self.user, "100")
        self.assertEqual(RoundBet.objects.count(), 1)


@SHORT_CHAIN
class BotTests(TestCase):
    def setUp(self):
        self.config = CrashBotSettings.load()
        self.round = services.open_round()

    def add_bots(self):
        for planned in bots.plan_round(self.round.betting_ends_at):
            bots.place(self.round.pk, planned)

    def test_the_admin_settings_decide_the_bets(self):
        CrashBotSettings.objects.update(count=5, min_bet="20.00", max_bet="30.00")
        self.add_bots()
        rows = CrashBotBet.objects.all()
        self.assertEqual(len(rows), 5)
        self.assertEqual(len({row.name for row in rows}), 5)
        for row in rows:
            self.assertTrue(Decimal("20") <= row.amount <= Decimal("30"))
            self.assertTrue(bots.MIN_TARGET <= row.target <= bots.MAX_TARGET)

    def test_switched_off(self):
        CrashBotSettings.objects.update(is_enabled=False)
        self.assertEqual(bots.plan_round(self.round.betting_ends_at), [])

    def test_never_more_bots_than_names(self):
        CrashBotSettings.objects.update(count=50, names="one\n\n two \n")
        self.assertEqual(len(bots.plan_round(self.round.betting_ends_at)), 2)

    def test_bets_come_inside_the_betting_window(self):
        start = self.round.betting_ends_at - timedelta(seconds=engine.BETTING_SECONDS)
        for planned in bots.plan_round(self.round.betting_ends_at):
            self.assertTrue(start <= planned.at < self.round.betting_ends_at)

    def test_no_bot_joins_a_flying_round(self):
        fly()
        planned = bots.PlannedBet(timezone.now(), "late", Decimal("10.00"), Decimal("2.00"))
        self.assertIsNone(bots.place(self.round.pk, planned))

    def test_runner_places_them_when_they_are_due(self):
        cycle = runner.Runner()
        cycle.planned_bots = [
            bots.PlannedBet(timezone.now(), "now", Decimal("10.00"), Decimal("2.00")),
            bots.PlannedBet(timezone.now() + timedelta(seconds=3), "later", Decimal("10.00"), Decimal("2.00")),
        ]
        cycle.step()
        self.assertEqual([bot.name for bot in CrashBotBet.objects.all()], ["now"])

    def test_bots_win_and_lose_without_touching_a_wallet(self):
        player = make_player("c")
        before = Transaction.objects.count()
        CrashBotBet.objects.create(round=self.round, name="winner", amount="100", target="1.50")
        CrashBotBet.objects.create(round=self.round, name="loser", amount="100", target="3.00")
        current = fly("2.00", seconds_ago=60)

        services.crash_round(current.pk)

        winner, loser = CrashBotBet.objects.order_by("id")
        self.assertEqual((winner.multiplier, winner.payout), (Decimal("1.50"), Decimal("150.00")))
        self.assertIsNone(loser.multiplier)
        self.assertEqual(Transaction.objects.count(), before)
        self.assertEqual(Wallet.objects.count(), 1)
        self.assertEqual(balance(player), Decimal("10000.00"))
        self.assertEqual(weekly_top(), [])

    def test_only_the_current_rounds_bots_are_kept(self):
        self.add_bots()
        services.start_flight(self.round.pk)
        services.crash_round(self.round.pk)
        services.open_round()
        self.assertFalse(CrashBotBet.objects.exists())

    def test_real_players_are_on_the_leaderboard_and_bots_are_not(self):
        player = make_player("c")
        services.place_bet(player, "100", "1.50")
        CrashBotBet.objects.create(round=self.round, name="bot", amount="100", target="1.50")
        services.crash_round(fly("2.00", seconds_ago=60).pk)
        self.assertEqual([row["player"] for row in weekly_top()], ["c"])


@SHORT_CHAIN
class SecretsTests(TestCase):
    """Until the crash, nothing public may show the seed or the crash point."""

    client_class = APIClient

    def setUp(self):
        self.round = services.open_round()

    def assert_secret(self, data):
        text = json.dumps(data)
        self.assertNotIn(self.round.seed, text)
        self.assertNotIn("crash_point", text.replace('"history"', ""))

    def test_snapshot_hides_a_live_round(self):
        self.assert_secret(feed.snapshot()["round"])
        fly()
        self.assert_secret(feed.snapshot()["round"])

    def test_snapshot_shows_a_crashed_round(self):
        fly("1.50", seconds_ago=60)
        services.crash_round(self.round.pk)
        data = feed.snapshot()
        self.assertEqual(data["round"]["crash_point"], "1.50")
        self.assertEqual(data["round"]["seed"], self.round.seed)
        self.assertEqual(data["history"], [{"number": self.round.number, "crash_point": "1.50"}])

    def test_history_keeps_the_last_20(self):
        for _ in range(22):
            services.start_flight(self.round.pk)
            services.crash_round(self.round.pk)
            self.round = services.open_round()
        history = feed.snapshot()["history"]
        self.assertEqual(len(history), 20)
        self.assertEqual(history[0]["number"], self.round.number - 1)

    def test_rounds_api_shows_only_crashed_rounds(self):
        self.assertEqual(self.client.get("/api/crash_rounds").json(), [])
        self.assertEqual(self.client.get(f"/api/crash_rounds/{self.round.number}").status_code, 404)
        fly()
        self.assertEqual(self.client.get("/api/crash_rounds").json(), [])

        services.crash_round(self.round.pk)
        row = self.client.get(f"/api/crash_rounds/{self.round.number}").json()
        self.assertEqual(row["seed"], self.round.seed)

    def test_admin_hides_a_live_rounds_secrets_and_the_chains_last_seed(self):
        staff = User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev")
        self.client.force_login(staff)
        for url in [
            f"/admin/crash/crashround/{self.round.pk}/change/",
            "/admin/crash/crashround/",
            f"/admin/crash/crashchain/{self.round.chain_id}/change/",
        ]:
            with self.subTest(url=url):
                page = self.client.get(url).content.decode()
                self.assertNotIn(self.round.seed, page)
                self.assertNotIn(self.round.chain.last_seed, page)

    def test_rounds_and_bets_are_read_only_in_the_admin(self):
        request = RequestFactory().get("/admin/")
        request.user = User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev")
        for model in [CrashChain, CrashRound, RoundBet]:
            with self.subTest(model=model.__name__):
                self.assertFalse(admin.site._registry[model].has_add_permission(request))
                self.assertFalse(admin.site._registry[model].has_change_permission(request))


class RunnerLockTests(TransactionTestCase):
    def setUp(self):
        self.addCleanup(self.release)

    def release(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT pg_advisory_unlock_all()")

    def in_a_new_connection(self, func):
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

    def test_only_one_runner_gets_the_lock(self):
        self.assertTrue(runner.acquire_lock())
        self.assertFalse(self.in_a_new_connection(runner.acquire_lock))

    def test_the_lock_is_free_when_the_first_runner_is_gone(self):
        self.assertTrue(self.in_a_new_connection(runner.acquire_lock))
        self.assertTrue(runner.acquire_lock())

    def test_a_second_run_crash_refuses_to_start(self):
        runner.acquire_lock()
        result = self.in_a_new_connection(lambda: call_command("run_crash"))
        self.assertIsInstance(result, CommandError)


class CashOutRaceTests(TransactionTestCase):
    """Real parallel requests on PostgreSQL: the round's row lock decides who was first."""

    def setUp(self):
        Game.objects.get_or_create(
            slug="neon-crash", defaults={"title": "Neon Crash", "category": "crash", "rtp": Decimal("97.00"), "is_active": True}
        )
        self.chain_length = mock.patch.object(services, "CHAIN_LENGTH", 200)
        self.chain_length.start()
        self.addCleanup(self.chain_length.stop)
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

    def test_every_bet_is_paid_or_lost_never_both(self):
        players = [make_player(f"p{i}") for i in range(12)]
        for player in players:
            services.place_bet(player, "100")
        fly("5.00", seconds_ago=10)

        funcs = [lambda player=player: services.cash_out(player) for player in players]
        funcs.insert(6, lambda: services.crash_round(self.round.pk))
        results = self.run_in_threads(funcs)

        outcomes = [r for r in results if not isinstance(r, CrashRound)]
        self.assertEqual(len(outcomes), 12)
        for outcome in outcomes:
            if isinstance(outcome, Exception):
                self.assertIsInstance(outcome, services.RoundConflict, repr(outcome))
                self.assertEqual(outcome.code, "too_late")

        self.round.refresh_from_db()
        self.assertEqual(self.round.status, "crashed")
        paid = [r for r in outcomes if isinstance(r, RoundBet)]
        self.assertEqual(RoundBet.objects.filter(status="cashed_out").count(), len(paid))
        self.assertEqual(RoundBet.objects.filter(status="lost").count(), 12 - len(paid))
        self.assertEqual(Transaction.objects.filter(kind="win").count(), len(paid))
        for player in players:
            self.assertEqual(ledger_sum(player), balance(player))

    def test_parallel_clicks_pay_once(self):
        player = make_player("double")
        services.place_bet(player, "100")
        fly("5.00", seconds_ago=10)

        results = self.run_in_threads([lambda: services.cash_out(player)] * 8)

        self.assertEqual(sum(isinstance(r, RoundBet) for r in results), 1, results)
        self.assertEqual(Transaction.objects.filter(kind="win").count(), 1)
        self.assertEqual(ledger_sum(player), balance(player))

    def test_parallel_bets_of_one_player_charge_once(self):
        player = make_player("twice")
        results = self.run_in_threads([lambda: services.place_bet(player, "100")] * 8)
        self.assertEqual(sum(isinstance(r, RoundBet) for r in results), 1, results)
        self.assertEqual(balance(player), Decimal("9900.00"))

    def test_a_bet_at_the_last_moment_is_in_or_out_never_lost_in_between(self):
        player = make_player("last")
        results = self.run_in_threads(
            [lambda: services.place_bet(player, "100"), lambda: services.start_flight(self.round.pk)]
        )
        if isinstance(results[0], RoundBet):
            self.assertEqual(balance(player), Decimal("9900.00"))
        else:
            self.assertEqual(results[0].code, "round_closed")
            self.assertEqual(balance(player), Decimal("10000.00"))


class ChannelLayerSettingsTests(SimpleTestCase):
    def test_redis_waits_longer_than_the_layers_own_blocking_read(self):
        self.assertGreater(settings.CHANNEL_REDIS_SOCKET_TIMEOUT, RedisChannelLayer.brpop_timeout)


class WebSocketTests(TransactionTestCase):
    """The sockets read rows from another thread, so the data must really be committed."""

    def setUp(self):
        Game.objects.get_or_create(
            slug="neon-crash", defaults={"title": "Neon Crash", "category": "crash", "rtp": Decimal("97.00"), "is_active": True}
        )
        self.chain_length = mock.patch.object(services, "CHAIN_LENGTH", 200)
        self.chain_length.start()
        self.addCleanup(self.chain_length.stop)

    async def connect(self, headers=ORIGIN):
        socket = WebsocketCommunicator(application, "/ws/crash", headers=headers)
        connected, _ = await socket.connect()
        self.assertTrue(connected)
        return socket

    async def test_new_client_gets_a_snapshot(self):
        current = await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        message = await socket.receive_json_from()
        self.assertEqual(message["type"], "snapshot")
        self.assertEqual(message["round"]["number"], current.number)
        self.assertEqual(message["round"]["status"], "betting")
        self.assertEqual(message["round"]["seed_hash"], current.seed_hash)
        self.assertNotIn("seed", message["round"])
        self.assertEqual((message["history"], message["bets"]), ([], []))
        self.assertIn("server_time", message)
        await socket.disconnect()

    async def test_snapshot_before_the_first_round(self):
        socket = await self.connect()
        self.assertIsNone((await socket.receive_json_from())["round"])
        await socket.disconnect()

    async def test_a_round_goes_out_live(self):
        user = await database_sync_to_async(make_player)("live")
        current = await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        await socket.receive_json_from()

        await database_sync_to_async(services.place_bet)(user, "100", "1.50")
        placed = await socket.receive_json_from()
        self.assertEqual(
            placed,
            {
                "type": "bet.placed",
                "id": placed["id"],
                "round": current.number,
                "player": "live",
                "amount": "100.00",
                "multiplier": None,
                "payout": "0.00",
                "is_bot": False,
            },
        )

        await database_sync_to_async(fly)("2.00", 60)
        flying = await socket.receive_json_from()
        self.assertEqual(flying["type"], "round.flying")
        self.assertIsNotNone(flying["started_at"])
        self.assertNotIn("crash_point", flying)

        await database_sync_to_async(services.crash_round)(current.pk)
        cashed = await socket.receive_json_from()
        self.assertEqual((cashed["type"], cashed["multiplier"], cashed["payout"]), ("bet.cashed_out", "1.50", "150.00"))
        crashed = await socket.receive_json_from()
        self.assertEqual((crashed["type"], crashed["crash_point"]), ("round.crashed", "2.00"))
        self.assertEqual(crashed["seed"], current.seed)
        await socket.disconnect()

    async def test_bots_are_marked_in_the_feed(self):
        current = await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        await socket.receive_json_from()

        planned = bots.PlannedBet(timezone.now(), "kite", Decimal("50.00"), Decimal("2.00"))
        await database_sync_to_async(bots.place)(current.pk, planned)

        message = await socket.receive_json_from()
        self.assertEqual((message["type"], message["player"], message["is_bot"]), ("bet.placed", "kite", True))
        await socket.disconnect()

        socket = await self.connect()
        self.assertTrue((await socket.receive_json_from())["bets"][0]["is_bot"])
        await socket.disconnect()

    async def test_clients_can_only_listen(self):
        await database_sync_to_async(services.open_round)()
        socket = await self.connect()
        await socket.receive_json_from()
        await socket.send_to(text_data="not json at all")
        await socket.send_json_to({"type": "bet.placed", "amount": "1"})
        self.assertTrue(await socket.receive_nothing())
        self.assertFalse(await database_sync_to_async(RoundBet.objects.exists)())
        await socket.disconnect()

    async def test_another_site_cannot_open_the_socket(self):
        for headers in [[(b"origin", b"https://evil.example")], [(b"origin", b"http://localhost:9999")], []]:
            with self.subTest(headers=headers):
                socket = WebsocketCommunicator(application, "/ws/crash", headers=headers)
                connected, _ = await socket.connect()
                self.assertFalse(connected)
                await socket.disconnect()

    async def test_a_cookie_changes_nothing(self):
        socket = await self.connect(ORIGIN + [(b"cookie", b"lumora_access=whatever")])
        await socket.receive_json_from()
        await socket.disconnect()


class LiveBetNameTests(TestCase):
    def test_a_live_bet_never_names_a_player_by_email(self):
        user = User.objects.create_user(username="private.name@lumora.dev", email="private.name@lumora.dev")
        open_wallet(user)
        current = services.open_round()
        bet = services.place_bet(user, "100")
        data = feed.bet_data(RoundBet.objects.select_related("user", "round").get(pk=bet.pk))
        self.assertRegex(data["player"], r"^Player [0-9a-f]{6}$")
        self.assertNotIn("private", str(data))
        self.assertNotIn(str(user.pk), data["player"])
        self.assertEqual(current.number, data["round"])
