from django.test import TestCase

from .models import Game


class GameApiTests(TestCase):
    """The catalogue is filled by migration 0002_seed_games and is public."""

    def test_catalogue_is_seeded_and_public(self):
        response = self.client.get("/api/games")
        self.assertEqual(response.status_code, 200)
        slugs = [g["slug"] for g in response.json()]
        self.assertEqual(slugs, ["neon-crash", "zeus-legacy", "lumora-roulette"])

    def test_inactive_games_are_hidden(self):
        Game.objects.filter(slug="neon-crash").update(is_active=False)
        slugs = [g["slug"] for g in self.client.get("/api/games").json()]
        self.assertNotIn("neon-crash", slugs)

    def test_filters(self):
        crash = self.client.get("/api/games?category=crash").json()
        self.assertEqual([g["slug"] for g in crash], ["neon-crash"])
        game = self.client.get("/api/games?slug=zeus-legacy").json()
        self.assertEqual(game[0]["rtp"], "96.50")

    def test_unknown_slug_returns_an_empty_list(self):
        response = self.client.get("/api/games?slug=does-not-exist")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_games_are_read_only(self):
        for method in ["post", "put", "patch", "delete"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)("/api/games/1")
                self.assertIn(response.status_code, (401, 403, 405))
