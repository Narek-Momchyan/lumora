from decimal import Decimal

from django.db.models import Sum
from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from fairness.models import SeedPair
from fairness.rng import first_float, hash_seed
from wallet.models import Wallet
from wallet.services import open_wallet
from . import engine


class CrashEngineTests(SimpleTestCase):
    def test_crash_point(self):
        self.assertEqual(engine.crash_point(0.0), Decimal("1.00"))  # 0.97 is raised to the minimum
        self.assertEqual(engine.crash_point(0.5), Decimal("1.94"))
        self.assertEqual(engine.crash_point(0.75), Decimal("3.88"))
        self.assertEqual(str(engine.crash_point(0.1182)), "1.10")  # always two decimals, as in the API
        with self.assertRaises(ValueError):
            engine.crash_point(1.0)

    def test_payout(self):
        self.assertEqual(engine.payout(Decimal("100"), Decimal("2.00"), Decimal("2.00")), Decimal("200.00"))
        self.assertEqual(engine.payout(Decimal("100"), Decimal("2.00"), Decimal("1.99")), Decimal("0.00"))

    def test_rtp_simulation_is_about_97_percent(self):
        """Monte Carlo over 200,000 provably fair rounds, the same check Zeus Legacy will get."""
        rounds = 200_000
        points = [engine.crash_point(first_float("sim-seed", "sim-client", n)) for n in range(rounds)]
        # The spread grows with the target, so 10x gets a wider band.
        for target, tolerance in [("1.50", 0.01), ("2.00", 0.01), ("10.00", 0.04)]:
            with self.subTest(target=target):
                target = Decimal(target)
                returned = sum(engine.payout(Decimal("1"), target, point) for point in points)
                rtp = float(returned) / rounds
                self.assertAlmostEqual(rtp, 0.97, delta=tolerance, msg=f"RTP at {target}x was {rtp:.4f}")


class CrashApiTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = User.objects.create_user(username="c@lumora.dev", email="c@lumora.dev")
        open_wallet(self.user)
        self.client.force_authenticate(self.user)

    def play(self, amount="10", target="2.00"):
        return self.client.post("/api/crash_bets", {"amount": amount, "target": target})

    def test_rounds_settle_and_the_ledger_matches_the_balance(self):
        for _ in range(20):
            response = self.play()
            self.assertEqual(response.status_code, 201, response.content)
        wallet = Wallet.objects.get(user=self.user)
        self.assertEqual(wallet.transactions.aggregate(total=Sum("amount"))["total"], wallet.balance)
        bets = self.client.get("/api/crash_bets").json()
        self.assertEqual(len(bets), 20)
        wins = sum(Decimal(b["payout"]) for b in bets)
        self.assertEqual(wallet.balance, Decimal("10000.00") - 20 * 10 + wins)

    def test_round_can_be_verified_after_the_seed_is_revealed(self):
        bet = self.play("5", "1.50").json()
        revealed = self.client.post("/api/seeds").json()["revealed"]
        self.assertEqual(hash_seed(revealed["server_seed"]), bet["server_seed_hash"])
        r = first_float(revealed["server_seed"], bet["client_seed"], bet["nonce"])
        self.assertEqual(str(engine.crash_point(r)), bet["crash_point"])
        self.assertEqual(bet["won"], Decimal(bet["crash_point"]) >= Decimal("1.50"))

    def test_bad_bets_are_rejected_and_cost_nothing(self):
        for amount, target in [("0.50", "2"), ("10", "1.00"), ("999999", "2"), ("abc", "2"), ("10", "1.505")]:
            with self.subTest(amount=amount, target=target):
                self.assertEqual(self.play(amount, target).status_code, 400)
        self.assertEqual(Wallet.objects.get(user=self.user).balance, Decimal("10000.00"))
        self.assertFalse(SeedPair.objects.filter(user=self.user, nonce__gt=0).exists())

    def test_nonce_goes_up_by_one_per_bet(self):
        self.play("1")
        self.play("1")
        self.assertEqual(SeedPair.objects.get(user=self.user, is_active=True).nonce, 2)

    def test_not_enough_lc(self):
        Wallet.objects.filter(user=self.user).update(balance=Decimal("5.00"))
        response = self.play("10")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"detail": "Not enough LC."})

    def test_players_see_only_their_own_rounds(self):
        self.play()
        other = User.objects.create_user(username="o@lumora.dev", email="o@lumora.dev")
        self.client.force_authenticate(other)
        self.assertEqual(self.client.get("/api/crash_bets").json(), [])

    def test_needs_a_token(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.play().status_code, 401)
