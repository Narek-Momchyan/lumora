import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from django.urls import reverse

from base.sample import load_sample, read_sample

from .models import Game, GameSound


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

    def test_every_game_is_playable(self):
        games = {g["slug"]: g for g in self.client.get("/api/games").json()}
        self.assertTrue(games["neon-crash"]["is_playable"])
        self.assertTrue(games["zeus-legacy"]["is_playable"])
        self.assertTrue(games["lumora-roulette"]["is_playable"])

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


MP3 = bytes([0xFF, 0xFB, 0x90]) + b"0" * 32  # the first bytes of an MP3 frame


class GameSoundTests(TestCase):
    """The sounds of Neon Crash and Lumora Roulette: uploaded in the admin, played only when they have a file."""

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

    def upload(self, code, name, content, **extra):
        row = GameSound.objects.get(code=code)
        data = {"code": code, "file": SimpleUploadedFile(name, content, content_type="audio/mpeg"), "is_active": "on", **extra}
        return self.client.post(reverse("admin:games_gamesound_change", args=[row.pk]), data, format="multipart")

    def admin(self):
        self.client.force_login(get_user_model().objects.create_superuser("a@lumora.dev", "a@lumora.dev"))

    def test_the_nine_keys_exist_without_files_and_nothing_is_played(self):
        self.assertEqual(
            set(GameSound.objects.values_list("code", flat=True)),
            {"crash_flight", "crash_boom", "cash_out", "bet_placed", "round_start", "roulette_spin",
             "roulette_ball_drop", "win", "lose"},
        )
        self.assertFalse(GameSound.objects.exclude(file="").exists())
        self.assertEqual(self.client.get("/api/game_sounds").json(), [])  # public, and empty until a file is uploaded

    def test_only_active_sounds_with_a_file_are_listed(self):
        self.admin()
        self.assertEqual(self.upload("win", "win.mp3", MP3).status_code, 302)
        GameSound.objects.filter(code="lose").update(file="sounds/games/off.mp3", is_active=False)
        self.client.logout()
        rows = self.client.get("/api/game_sounds").json()
        self.assertEqual([row["code"] for row in rows], ["win"])
        self.assertRegex(rows[0]["file"], r"^https?://.+/media/sounds/games/win.*\.mp3$")  # a full URL

    def test_every_audio_format_is_accepted(self):
        self.admin()
        for name, content in [
            ("a.mp3", MP3), ("a.ogg", b"OggS" + b"0" * 32), ("a.wav", b"RIFF\x00\x00\x00\x00WAVE" + b"0" * 32),
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.upload("cash_out", name, content).status_code, 302)

    def test_the_admin_rejects_files_that_are_not_audio_or_too_big(self):
        self.admin()
        for name, content in [
            ("evil.html", b"<script></script>"), ("evil.mp3", b"not really audio"), ("a.txt", MP3),
            ("big.mp3", MP3 + b"0" * (10 * 1024 * 1024)),
        ]:
            with self.subTest(name=name):
                self.assertEqual(self.upload("bet_placed", name, content).status_code, 200)
                self.assertEqual(GameSound.objects.get(code="bet_placed").file.name, "")

    def test_an_unknown_key_and_a_second_row_for_a_key_are_refused(self):
        with self.assertRaises(ValidationError):
            GameSound(code="explosion").full_clean()
        with self.assertRaises(IntegrityError), transaction.atomic():
            GameSound.objects.create(code="win")

    def test_the_sample_has_no_sound_files(self):
        self.assertNotIn("game_sounds", read_sample())  # no binary files in the sample: the keys come from a migration


class SoundButtonTextTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def test_both_pages_have_the_button_texts_in_every_language(self):
        for page in ("crash_page_labels", "roulette_page_labels"):
            texts = {}
            for lang in ("en", "am", "ru"):
                row = self.client.get(f"/api/{page}?lang={lang}").json()[0]
                texts[lang] = (row["sound_on"], row["sound_off"], row["sound_volume"])
                self.assertTrue(all(text.strip() for text in texts[lang]), (page, lang))
            self.assertEqual(len(set(texts.values())), 3, page)  # three different sets, none copied from English
