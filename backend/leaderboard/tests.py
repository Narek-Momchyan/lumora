from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from accounts.models import User
from wallet import services
from wallet.models import Transaction
from .services import weekly_top


def make_player(name):
    email = f"{name}@lumora.dev"
    user = User.objects.create_user(username=email, email=email, display_name=name)
    return services.open_wallet(user)


class LeaderboardTests(TestCase):
    def setUp(self):
        self.arman = make_player("arman")
        self.nova = make_player("nova")
        services.debit(self.arman, 100, game="neon-crash")
        services.credit(self.arman, 300, game="neon-crash")
        services.debit(self.nova, 100, game="neon-crash")
        services.claim_daily_bonus(self.nova)  # bonuses do not count

    def test_ranks_by_net_game_result(self):
        top = weekly_top()
        self.assertEqual([row["player"] for row in top], ["arman", "nova"])
        self.assertEqual([row["net"] for row in top], [200, -100])
        self.assertEqual([row["bets"] for row in top], [1, 1])

    def test_older_than_a_week_does_not_count(self):
        Transaction.objects.filter(wallet=self.arman).update(created_at=timezone.now() - timedelta(days=8))
        self.assertEqual([row["player"] for row in weekly_top()], ["nova"])

    def test_api_is_public_and_returns_money_as_strings(self):
        rows = self.client.get("/api/leaderboard").json()
        self.assertEqual(rows[0], {"rank": 1, "player": "arman", "net": "200.00", "bets": 1})


class NoEmailInTheLeaderboardTests(TestCase):
    def test_a_player_without_a_display_name_is_never_shown_by_email_or_id(self):
        user = User.objects.create_user(username="secret.person@lumora.dev", email="secret.person@lumora.dev")
        wallet = services.open_wallet(user)
        services.debit(wallet, "100.00", game="crash", round_id="r1", idempotency_key="b1")
        services.credit(wallet, "300.00", game="crash", round_id="r1", idempotency_key="w1")
        response = self.client.get("/api/leaderboard")
        row = response.json()[0]
        self.assertRegex(row["player"], r"^Player [0-9a-f]{6}$")
        body = response.content.decode()
        self.assertNotIn("secret", body)
        self.assertNotIn("lumora.dev", body)
        self.assertEqual(set(row), {"rank", "player", "net", "bets"})  # no id, no email
