import shutil
import tempfile
from decimal import Decimal
from io import StringIO
from itertools import cycle
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Sum
from django.test import SimpleTestCase, TestCase, override_settings, tag
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from fairness.models import SeedPair
from fairness.rng import float_stream, hash_seed
from games.models import Game
from leaderboard.services import weekly_top
from wallet.models import JackpotPool, Transaction, Wallet
from wallet.services import InsufficientFunds, open_wallet
from . import engine, services
from .models import SlotSound, SlotSpin
from .simulation import simulate

SPREAD = [i / 18 for i in range(18)]  # one of every symbol kind of value: no 8 of a kind


def grid_of(*symbols):
    """A grid that starts with `symbols` and has no other win: filler symbols never reach 8."""
    filler = cycle(["shield", "chalice", "red_stone", "purple_stone", "yellow_stone", "green_stone", "blue_stone"])
    cells = list(symbols) + [next(filler) for _ in range(engine.ROWS * engine.COLS - len(symbols))]
    return [cells[i : i + engine.COLS] for i in range(0, len(cells), engine.COLS)]


def spin_on(grid, **kwargs):
    """One spin on a fixed grid. The tumble after a win leaves a grid without new wins."""

    def no_new_wins(current, winning, stream, table):
        removed = set(winning)
        kept = [symbol for r, row in enumerate(current) for c, symbol in enumerate(row) if (r, c) not in removed]
        return grid_of(*[symbol for symbol in kept if symbol in engine.MULTIPLIERS or symbol == engine.SCATTER])

    with mock.patch.object(engine, "new_grid", return_value=grid), mock.patch.object(engine, "tumble", no_new_wins):
        return engine.play_spin(iter(cycle(SPREAD)), **kwargs)


class ZeusPayTests(SimpleTestCase):
    def test_a_symbol_pays_from_8_with_three_bands(self):
        pays = {count: engine.symbol_pay("trident", count) for count in [7, 8, 9, 10, 11, 12, 30]}
        self.assertEqual(pays, {7: 0, 8: 1000, 9: 1000, 10: 2500, 11: 2500, 12: 5000, 30: 5000})

    def test_the_paytable_is_the_zeus_legacy_one(self):
        self.assertEqual(engine.PAYTABLE["blue_stone"], (25, 75, 200))
        self.assertEqual(engine.PAYTABLE["pegasus"], (250, 1000, 2500))
        self.assertEqual(engine.SCATTER_PAY, {4: 300, 5: 500, 6: 10_000})

    def test_scatters_pay_the_same_from_6(self):
        self.assertEqual([engine.scatter_pay(n) for n in [4, 5, 6, 7]], [300, 500, 10_000, 10_000])

    def test_evaluate_finds_winning_symbols_anywhere(self):
        grid = grid_of(*["trident"] * 8)
        wins, winning, pay = engine.evaluate(grid)
        self.assertEqual(wins, [{"symbol": "trident", "count": 8, "pay": 1000}])
        self.assertEqual(len(winning), 8)
        self.assertEqual(pay, 1000)

    def test_scatters_and_multipliers_are_not_symbol_wins(self):
        grid = grid_of(*[engine.SCATTER] * 8, *["mult_2"] * 8)
        self.assertEqual(engine.evaluate(grid), ([], [], 0))

    def test_tumble_keeps_the_rest_and_fills_from_the_top(self):
        grid = grid_of("trident", "trident")
        below = [grid[row][0] for row in range(1, engine.ROWS)]
        result = engine.tumble(grid, [(0, 0), (0, 1)], iter([0.0, 0.0]), engine.BASE_TABLE)
        self.assertEqual([result[row][0] for row in range(1, engine.ROWS)], below)
        self.assertEqual(result[0][:2], ["trident", "trident"])
        self.assertEqual(result[1:], grid[1:])

    def test_a_draw_follows_the_weights(self):
        self.assertEqual(engine.draw(iter([0.0]), engine.BASE_TABLE), "trident")
        self.assertEqual(engine.draw(iter([0.9999999]), engine.BASE_TABLE), "mult_100")
        self.assertEqual(engine.draw(iter([0.9999999]), engine.FREE_TABLE), "mult_500")
        self.assertEqual(engine.draw(iter([0.9999999]), engine.NO_MULTIPLIER_TABLE), engine.SCATTER)


class ZeusSpinTests(SimpleTestCase):
    def test_multipliers_multiply_the_symbol_win(self):
        spin = spin_on(grid_of(*["trident"] * 8, "mult_2", "mult_5"))
        self.assertEqual(spin["collected_multipliers"], [2, 5])
        self.assertEqual(spin["win"], 1000 * 7)

    def test_scatter_wins_are_never_multiplied(self):
        spin = spin_on(grid_of(*["trident"] * 8, *[engine.SCATTER] * 4, "mult_2"))
        self.assertEqual(spin["win"], 1000 * 2 + 300)
        self.assertEqual(spin["free_spins_awarded"], engine.FREE_SPINS_AWARD)

    def test_a_spin_without_a_win_collects_nothing(self):
        spin = spin_on(grid_of("mult_100", "mult_50"))
        self.assertEqual(spin["collected_multipliers"], [])
        self.assertEqual(spin["global_multiplier"], 0)
        self.assertEqual(spin["win"], 0)

    def test_free_spins_add_new_multipliers_to_the_carried_one(self):
        spin = spin_on(grid_of(*["trident"] * 8, "mult_2"), is_free_spin=True, global_multiplier=10)
        self.assertEqual(spin["global_multiplier"], 12)
        self.assertEqual(spin["win"], 1000 * 12)

    def test_the_carried_multiplier_needs_a_new_one_in_the_spin(self):
        spin = spin_on(grid_of(*["trident"] * 8), is_free_spin=True, global_multiplier=10)
        self.assertEqual(spin["global_multiplier"], 10)
        self.assertEqual(spin["win"], 1000)

    def test_scatters_during_free_spins_retrigger_5(self):
        spin = spin_on(grid_of(*[engine.SCATTER] * 4), is_free_spin=True)
        self.assertEqual(spin["free_spins_awarded"], engine.FREE_SPINS_RETRIGGER)

    def test_a_spin_is_capped_at_1000x(self):
        spin = spin_on(grid_of(*["trident"] * 12, "mult_100", "mult_100", "mult_100"))
        self.assertEqual(spin["win"], engine.MAX_WIN)
        self.assertTrue(spin["is_max_win"])

    def test_a_bought_spin_is_capped_at_10x_and_has_scatters(self):
        spin = spin_on(grid_of(*["trident"] * 12), bought=True)
        self.assertEqual(spin["win"], engine.BONUS_BUY_SPIN_MAX_WIN)
        self.assertEqual(spin["free_spins_awarded"], engine.FREE_SPINS_AWARD)

    def test_bought_spins_have_no_multipliers(self):
        for nonce in range(200):
            spin = engine.play_spin(float_stream("seed", "client", nonce), bought=True)
            with self.subTest(nonce=nonce):
                cells = [symbol for step in spin["steps"] for row in step["grid"] for symbol in row]
                self.assertFalse(set(cells) & set(engine.MULTIPLIERS))
                self.assertGreaterEqual(sum(row.count(engine.SCATTER) for row in spin["steps"][0]["grid"]), 4)

    def test_tumbles_stop_at_the_limit(self):
        grid = grid_of(*["trident"] * 8)
        with mock.patch.object(engine, "new_grid", return_value=grid), mock.patch.object(
            engine, "tumble", return_value=grid
        ):
            spin = engine.play_spin(iter(cycle(SPREAD)))
        self.assertEqual(spin["win"], 1000 * engine.MAX_TUMBLES)
        self.assertEqual(len(spin["steps"]), engine.MAX_TUMBLES + 1)


def round_of(*spins):
    """play_round() with these spins instead of random ones."""
    keys = {"win": 0, "free_spins_awarded": 0, "is_max_win": False, "global_multiplier": 0}
    with mock.patch.object(engine, "play_spin", side_effect=[{**keys, **spin} for spin in spins]) as play:
        return engine.play_round(iter([])), play


class ZeusRoundTests(SimpleTestCase):
    def test_a_spin_without_scatters_is_the_whole_round(self):
        result, play = round_of({"win": 150})
        self.assertEqual(result["total_win"], 150)
        self.assertEqual(result["free_spins_played"], 0)
        self.assertEqual(play.call_count, 1)

    def test_free_spins_play_to_the_end_and_add_up(self):
        result, _ = round_of({"free_spins_awarded": 2}, {"win": 100}, {"win": 200})
        self.assertEqual(result["total_win"], 300)
        self.assertEqual(result["free_spins_played"], 2)

    def test_a_retrigger_adds_spins(self):
        result, _ = round_of({"free_spins_awarded": 1}, {"free_spins_awarded": 5}, *[{"win": 10}] * 5)
        self.assertEqual(result["free_spins_played"], 6)

    def test_every_spin_says_how_many_free_spins_are_left(self):
        result, _ = round_of({"free_spins_awarded": 2}, {"free_spins_awarded": 5}, *[{}] * 6)
        self.assertEqual([spin["free_spins_left"] for spin in result["spins"]], [2, 6, 5, 4, 3, 2, 1, 0])

    def test_the_multiplier_carries_to_the_next_free_spin(self):
        _, play = round_of({"free_spins_awarded": 2}, {"global_multiplier": 7}, {})
        self.assertEqual(play.call_args_list[2].kwargs["global_multiplier"], 7)

    def test_the_max_win_ends_the_bonus(self):
        result, _ = round_of({"free_spins_awarded": 15}, {"win": engine.MAX_WIN, "is_max_win": True})
        self.assertEqual(result["free_spins_played"], 1)

    def test_the_max_win_on_the_paid_spin_keeps_the_free_spins(self):
        result, _ = round_of({"free_spins_awarded": 1, "win": engine.MAX_WIN, "is_max_win": True}, {"win": 5})
        self.assertEqual(result["free_spins_played"], 1)

    def test_the_same_seeds_give_the_same_round(self):
        first = engine.play_round(float_stream("seed", "client", 7))
        second = engine.play_round(float_stream("seed", "client", 7))
        self.assertEqual(first, second)

    def test_wins_are_whole_numbers(self):
        for nonce in range(300):
            result = engine.play_round(float_stream("seed", "client", nonce))
            self.assertIsInstance(result["total_win"], int)

    def test_a_bought_round_always_has_free_spins(self):
        for nonce in range(20):
            result = engine.play_round(float_stream("seed", "client", nonce), bonus_buy=True)
            self.assertGreaterEqual(result["free_spins_played"], 1)

    def test_win_amount_rounds_down_to_cents(self):
        self.assertEqual(engine.win_amount(Decimal("0.20"), 25), Decimal("0.05"))
        self.assertEqual(engine.win_amount(Decimal("0.33"), 25), Decimal("0.08"))
        self.assertEqual(engine.win_amount(Decimal("100.00"), engine.MAX_WIN), Decimal("100000.00"))

    def test_a_bonus_buy_costs_100_bets(self):
        self.assertEqual(engine.stake_for(Decimal("0.20"), True), Decimal("20.00"))
        self.assertEqual(engine.stake_for(Decimal("0.20"), False), Decimal("0.20"))


class ZeusJackpotRulesTests(SimpleTestCase):
    def test_the_chance_grows_with_the_stake(self):
        self.assertAlmostEqual(engine.jackpot_chance("MINI", Decimal("100")), 0.002)
        self.assertAlmostEqual(engine.jackpot_chance("GRAND", Decimal("100")), 0.0000004)

    def test_the_biggest_stake_stays_far_from_a_sure_win(self):
        stake = engine.stake_for(Decimal("100"), True)
        self.assertLess(sum(engine.jackpot_chance(tier, stake) for tier in engine.JACKPOT_TIERS), 0.25)

    def test_the_roll_goes_from_the_rarest_tier(self):
        stake = Decimal("100")
        self.assertEqual(engine.roll_jackpot(stake, 0.0), "GRAND")
        self.assertEqual(engine.roll_jackpot(stake, 0.0021), "MINI")
        self.assertIsNone(engine.roll_jackpot(stake, 0.5))


@tag("slow")
class ZeusRtpSimulationTests(SimpleTestCase):
    """manage.py test --tag slow. 5,000,000 rounds measured 96.44% in all, ±0.65% at 95% confidence."""

    def test_rtp_over_one_million_rounds(self):
        result = simulate(1_000_000)
        print(result)
        self.assertGreater(result["rtp_total"], 94.0)
        self.assertLess(result["rtp_total"], 99.0)

    def test_bonus_buy_rtp(self):
        result = simulate(50_000, bonus_buy=True)
        print(result)
        self.assertGreater(result["rtp_total"], 93.0)
        self.assertLess(result["rtp_total"], 100.0)


class SlotSpinApiTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = User.objects.create_user(username="z@lumora.dev", email="z@lumora.dev")
        self.wallet = open_wallet(self.user)
        self.client.force_authenticate(self.user)
        Game.objects.filter(slug=services.GAME_SLUG).update(is_playable=True)

    def spin(self, amount="1.00", bonus_buy=False, game=services.GAME_SLUG):
        return self.client.post("/api/slot_spins", {"game": game, "amount": amount, "bonus_buy": bonus_buy})

    def pools(self):
        return dict(JackpotPool.objects.values_list("tier", "amount"))

    def assert_nothing_happened(self):
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))
        self.assertFalse(SeedPair.objects.filter(user=self.user, nonce__gt=0).exists())
        self.assertFalse(SlotSpin.objects.exists())

    def test_spins_settle_and_the_ledger_matches_the_balance(self):
        for _ in range(40):
            self.assertEqual(self.spin("0.20").status_code, 201)
        self.wallet.refresh_from_db()
        ledger = self.wallet.transactions.aggregate(total=Sum("amount"))["total"]
        self.assertEqual(ledger, self.wallet.balance)

        spins = SlotSpin.objects.all()
        expected = Decimal("10000.00") - sum(s.cost for s in spins) + sum(s.payout + s.jackpot_win for s in spins)
        self.assertEqual(self.wallet.balance, expected)

    def test_a_spin_returns_everything_the_frontend_needs(self):
        body = self.spin().json()
        self.assertEqual(body["game"], services.GAME_SLUG)
        self.assertEqual(body["cost"], "1.00")
        self.assertIn("steps", body["result"]["spins"][0])
        self.assertEqual(set(body["jackpot_pools"]), set(engine.JACKPOT_TIERS))
        self.wallet.refresh_from_db()
        self.assertEqual(body["balance"], str(self.wallet.balance))

    def test_a_win_is_the_engine_total_in_lc(self):
        body = self.spin("0.20", bonus_buy=True).json()
        expected = engine.win_amount(Decimal("0.20"), body["result"]["total_win"])
        self.assertEqual(Decimal(body["payout"]), expected)

    def test_a_bonus_buy_charges_100_bets_and_plays_the_free_spins_at_once(self):
        body = self.spin("0.20", bonus_buy=True).json()
        self.assertEqual(body["cost"], "20.00")
        self.assertGreaterEqual(body["free_spins_played"], engine.FREE_SPINS_AWARD - 1)
        self.assertEqual(len(body["result"]["spins"]), body["free_spins_played"] + 1)
        bet = self.wallet.transactions.get(kind=Transaction.Kind.BET)
        self.assertEqual(bet.amount, Decimal("-20.00"))
        self.assertEqual(bet.game, services.GAME_SLUG)

    def test_one_round_uses_one_nonce(self):
        self.spin("0.20", bonus_buy=True)
        self.spin("0.20", bonus_buy=True)
        self.assertEqual(SeedPair.objects.get(user=self.user).nonce, 2)
        self.assertEqual(list(SlotSpin.objects.order_by("id").values_list("nonce", flat=True)), [0, 1])

    def test_a_round_can_be_verified_after_the_seed_is_revealed(self):
        body = self.spin("0.20", bonus_buy=True).json()
        revealed = self.client.post("/api/seeds").json()["revealed"]
        self.assertEqual(hash_seed(revealed["server_seed"]), body["server_seed_hash"])

        stream = float_stream(revealed["server_seed"], body["client_seed"], body["nonce"])
        tier = engine.roll_jackpot(Decimal(body["cost"]), next(stream))
        self.assertEqual(tier or "", body["jackpot_tier"])
        self.assertEqual(engine.play_round(stream, bonus_buy=True), body["result"])

    def test_the_list_is_short_and_one_spin_has_the_result(self):
        spin_id = self.spin().json()["id"]
        row = self.client.get("/api/slot_spins").json()[0]
        self.assertNotIn("result", row)
        self.assertIn("result", self.client.get(f"/api/slot_spins/{spin_id}").json())

    def test_the_list_has_the_last_50(self):
        spin = services.play_spin(self.user, services.GAME_SLUG, Decimal("0.20"))
        fields = {field.name: getattr(spin, field.name) for field in SlotSpin._meta.concrete_fields if field.name != "id"}
        SlotSpin.objects.bulk_create([SlotSpin(**fields) for _ in range(60)])
        self.assertEqual(len(self.client.get("/api/slot_spins").json()), 50)

    def test_spins_are_private(self):
        spin_id = self.spin().json()["id"]
        other = User.objects.create_user(username="o@lumora.dev", email="o@lumora.dev")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get("/api/slot_spins").json(), [])
        self.assertEqual(self.client.get(f"/api/slot_spins/{spin_id}").status_code, 404)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/slot_spins").status_code, 401)
        self.assertEqual(self.spin().status_code, 401)

    def test_a_game_that_is_not_playable_takes_no_bets(self):
        Game.objects.filter(slug=services.GAME_SLUG).update(is_playable=False)
        response = self.spin()
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "game_unavailable")
        self.assert_nothing_happened()

    def test_only_real_slot_games_can_be_played(self):
        for game in ["no-such-game", "neon-crash"]:
            with self.subTest(game=game):
                self.assertEqual(self.spin(game=game).json()["code"], "game_not_found")
        self.assert_nothing_happened()

    def test_bets_outside_the_limits_cost_nothing(self):
        for amount in ["0.19", "100.01"]:
            with self.subTest(amount=amount):
                body = self.spin(amount).json()
                self.assertEqual(body["code"], "bet_out_of_range")
                self.assertIn("0.20", body["detail"])
        self.assert_nothing_happened()

    def test_too_little_lc_costs_nothing(self):
        pools = self.pools()
        Game.objects.filter(slug=services.GAME_SLUG).update(max_bet=Decimal("1000.00"))
        response = self.spin("150.00", bonus_buy=True)
        self.assertEqual(response.json()["code"], "not_enough_lc")
        self.assert_nothing_happened()
        self.assertEqual(self.pools(), pools)

    def test_a_failure_during_the_round_charges_nothing(self):
        pools = self.pools()
        with mock.patch.object(engine, "play_round", side_effect=RuntimeError("boom")):
            with self.assertRaises(RuntimeError):
                services.play_spin(self.user, services.GAME_SLUG, Decimal("1.00"))
        self.assert_nothing_happened()
        self.assertEqual(self.pools(), pools)
        self.assertEqual(self.wallet.transactions.count(), 1)  # only the signup grant

    def test_every_paid_stake_grows_the_pools(self):
        before = self.pools()
        self.spin("0.20")
        after = self.pools()
        for tier, rate in engine.JACKPOT_RATES.items():
            with self.subTest(tier=tier):
                self.assertEqual(after[tier] - before[tier], Decimal("0.20") * rate)

    def test_a_jackpot_pays_the_pool_and_resets_it(self):
        JackpotPool.objects.filter(tier="MINI").update(amount=Decimal("123.456789"))
        with mock.patch.object(engine, "roll_jackpot", return_value="MINI"):
            body = self.spin("1.00").json()

        self.assertEqual(body["jackpot_tier"], "MINI")
        self.assertEqual(body["jackpot_win"], "123.45")  # the pool with this stake's share, rounded down
        self.assertEqual(self.pools()["MINI"], engine.JACKPOT_SEEDS["MINI"])
        paid = self.wallet.transactions.get(kind=Transaction.Kind.JACKPOT)
        self.assertEqual(paid.amount, Decimal("123.45"))

        self.wallet.refresh_from_db()
        ledger = self.wallet.transactions.aggregate(total=Sum("amount"))["total"]
        self.assertEqual(ledger, self.wallet.balance)

    def test_a_jackpot_counts_on_the_leaderboard(self):
        with mock.patch.object(engine, "roll_jackpot", return_value="GRAND"):
            self.spin("1.00")
        self.assertGreater(Decimal(weekly_top()[0]["net"]), Decimal("40000"))

    def test_money_changes_only_in_the_wallet(self):
        wallet_before = Wallet.objects.get(pk=self.wallet.pk).balance
        with mock.patch.object(services.wallet_services, "debit", side_effect=InsufficientFunds("no")):
            self.assertEqual(self.spin().status_code, 400)
        self.assertEqual(Wallet.objects.get(pk=self.wallet.pk).balance, wallet_before)


MP3 = b"ID3\x04\x00\x00\x00\x00\x00\x00" + b"0" * 32


class SlotContentTests(TestCase):
    client_class = APIClient

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_root = tempfile.mkdtemp()
        cls.media_override = override_settings(MEDIA_ROOT=cls.media_root)
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        shutil.rmtree(cls.media_root, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.client.force_login(get_user_model().objects.create_superuser("a@lumora.dev", "a@lumora.dev"))

    def add_sound(self, name, content):
        upload = SimpleUploadedFile(name, content, content_type="audio/mpeg")
        data = {"code": SlotSound.Code.BIG_WIN, "file": upload, "is_active": "on"}
        return self.client.post(reverse("admin:slots_slotsound_add"), data, format="multipart")

    def test_jackpot_pools_are_public_in_whole_cents(self):
        JackpotPool.objects.filter(tier="MINI").update(amount=Decimal("100.123456"))
        self.client.logout()
        rows = {row["tier"]: row["amount"] for row in self.client.get("/api/jackpot_pools").json()}
        self.assertEqual(rows["MINI"], "100.12")
        self.assertEqual(set(rows), set(engine.JACKPOT_TIERS))

    def test_the_api_lists_only_sounds_that_can_be_played(self):
        SlotSound.objects.create(code=SlotSound.Code.MEGA_WIN)
        SlotSound.objects.create(code=SlotSound.Code.ULTRA_WIN, file="sounds/zeus/off.mp3", is_active=False)
        self.assertEqual(self.add_sound("win.mp3", MP3).status_code, 302)

        rows = self.client.get("/api/slot_sounds").json()
        self.assertEqual([row["code"] for row in rows], ["big_win"])
        self.assertIn("/media/sounds/zeus/win", rows[0]["file"])

    def test_every_audio_format_is_accepted(self):
        for name, content in [
            ("a.mp3", b"\xff\xfb\x90" + b"0" * 32),
            ("a.ogg", b"OggS" + b"0" * 32),
            ("a.wav", b"RIFF\x00\x00\x00\x00WAVE" + b"0" * 32),
        ]:
            with self.subTest(name=name):
                SlotSound.objects.all().delete()
                self.assertEqual(self.add_sound(name, content).status_code, 302)

    def test_the_admin_rejects_files_that_are_not_audio(self):
        for name, content in [("evil.html", b"<script></script>"), ("evil.mp3", b"not really audio"), ("a.txt", MP3)]:
            with self.subTest(name=name):
                self.assertEqual(self.add_sound(name, content).status_code, 200)
                self.assertFalse(SlotSound.objects.exists())

    def test_the_admin_rejects_audio_over_the_size_limit(self):
        self.assertEqual(self.add_sound("big.mp3", MP3 + b"0" * (10 * 1024 * 1024)).status_code, 200)
        self.assertFalse(SlotSound.objects.exists())

    def load_sounds(self, content=MP3, **options):
        with mock.patch("slots.management.commands.load_sounds.download", return_value=content) as download:
            call_command("load_sounds", stdout=StringIO(), stderr=StringIO(), **options)
        return download

    def test_load_sounds_creates_a_playable_row_for_every_code(self):
        self.load_sounds()

        self.assertEqual(set(SlotSound.objects.values_list("code", flat=True)), set(SlotSound.Code.values))
        rows = self.client.get("/api/slot_sounds").json()
        self.assertEqual(len(rows), len(SlotSound.Code.values))
        self.assertTrue(all("/media/sounds/zeus/" in row["file"] for row in rows))

    def test_load_sounds_keeps_a_sound_changed_in_the_admin(self):
        self.assertEqual(self.add_sound("mine.mp3", MP3).status_code, 302)
        mine = SlotSound.objects.get(code=SlotSound.Code.BIG_WIN).file.name

        self.load_sounds()

        self.assertEqual(SlotSound.objects.get(code=SlotSound.Code.BIG_WIN).file.name, mine)

    def test_load_sounds_force_replaces_the_file(self):
        self.load_sounds()
        sound = SlotSound.objects.get(code=SlotSound.Code.BIG_WIN)
        old_file, storage = sound.file.name, sound.file.storage

        self.load_sounds(force=True)

        sound.refresh_from_db()
        self.assertNotEqual(sound.file.name, old_file)
        self.assertFalse(storage.exists(old_file))
        self.assertEqual(SlotSound.objects.count(), len(SlotSound.Code.values))

    def test_load_sounds_reports_a_download_that_is_not_audio(self):
        with self.assertRaisesMessage(CommandError, "big_win"):
            self.load_sounds(content=b"<html>not found</html>")
        self.assertFalse(SlotSound.objects.exists())
