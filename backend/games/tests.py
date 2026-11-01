from django.conf import settings
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
        self.assertEqual(game[0]["rtp"], "96.60")

    def test_neon_crash_and_zeus_legacy_are_playable_and_roulette_is_coming_soon(self):
        games = {g["slug"]: g for g in self.client.get("/api/games").json()}
        self.assertTrue(games["neon-crash"]["is_playable"])
        self.assertTrue(games["zeus-legacy"]["is_playable"])
        self.assertFalse(games["lumora-roulette"]["is_playable"])

    def test_lumora_roulette_has_the_rtp_of_a_single_zero(self):
        game = self.client.get("/api/games?slug=lumora-roulette").json()[0]
        self.assertEqual(game["rtp"], "97.30")

    def test_zeus_legacy_has_its_limits_and_picture(self):
        game = self.client.get("/api/games?slug=zeus-legacy").json()[0]
        self.assertEqual((game["min_bet"], game["max_bet"]), ("0.20", "100.00"))
        self.assertEqual(game["image"], f"{settings.PUBLIC_BASE_URL}/media/images/zeus/zeus.png")

    def test_a_game_without_an_image_returns_null(self):
        self.assertIsNone(self.client.get("/api/games?slug=neon-crash").json()[0]["image"])

    def test_a_game_image_is_a_full_url(self):
        Game.objects.filter(slug="neon-crash").update(image="images/games/neon.png")
        image = self.client.get("/api/games?slug=neon-crash").json()[0]["image"]
        self.assertEqual(image, f"{settings.PUBLIC_BASE_URL}/media/images/games/neon.png")

    def test_unknown_slug_returns_an_empty_list(self):
        response = self.client.get("/api/games?slug=does-not-exist")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_games_are_read_only(self):
        for method in ["post", "put", "patch", "delete"]:
            with self.subTest(method=method):
                response = getattr(self.client, method)("/api/games/1")
                self.assertIn(response.status_code, (401, 403, 405))
