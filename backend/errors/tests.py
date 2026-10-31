from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import User
from base.sample import load_sample, read_sample
from crash.engine import MAX_TARGET, MIN_TARGET
from games.models import Game
from wallet.services import open_wallet
from .handlers import fill
from .models import ErrorMessage

PASSWORD = "Neon-Crash-2026"


class FillTests(SimpleTestCase):
    def test_placeholders_are_filled_and_unknown_ones_stay(self):
        self.assertEqual(fill("From {min} to {max}", {"min": 1, "max": 2}), "From 1 to 2")
        self.assertEqual(fill("From {min} to {typo}", {"min": 1}), "From 1 to {typo}")


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])  # fast, tests only
class ErrorTranslationTests(TestCase):
    client_class = APIClient

    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def text(self, code, lang):
        return ErrorMessage.objects.get(code=code, lang=lang).text

    def login(self, password="wrong-password"):
        return self.client.post("/api/token", {"email": "e@lumora.dev", "password": password})

    def play_as_a_player(self, amount, target):
        user = User.objects.create_user(username="p@lumora.dev", email="p@lumora.dev")
        open_wallet(user)
        self.client.force_authenticate(user)
        return self.client.post("/api/crash_bets", {"amount": amount, "target": target})

    def test_english_is_the_default(self):
        response = self.client.get("/api/me")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"code": "not_authenticated", "detail": "Log in to continue."})

    def test_lang_cookie_translates_errors(self):
        for lang in ["am", "ru"]:
            with self.subTest(lang=lang):
                self.client.cookies["lang"] = lang
                body = self.client.get("/api/me").json()
                self.assertEqual(body["code"], "not_authenticated")
                self.assertEqual(body["detail"], self.text("not_authenticated", lang))

    def test_query_parameter_beats_the_cookie(self):
        self.client.cookies["lang"] = "am"
        body = self.client.get("/api/me?lang=ru").json()
        self.assertEqual(body["detail"], self.text("not_authenticated", "ru"))

    def test_an_unknown_language_falls_back_to_english(self):
        self.client.cookies["lang"] = "de"
        self.assertEqual(self.client.get("/api/me").json()["detail"], "Log in to continue.")

    def test_a_missing_translation_falls_back_to_english(self):
        ErrorMessage.objects.filter(code="not_authenticated", lang="am").delete()
        self.client.cookies["lang"] = "am"
        self.assertEqual(self.client.get("/api/me").json()["detail"], "Log in to continue.")

    def test_a_code_without_any_text_keeps_the_code_and_the_default_text(self):
        ErrorMessage.objects.filter(code="not_authenticated").delete()
        body = self.client.get("/api/me").json()
        self.assertEqual(body["code"], "not_authenticated")
        self.assertEqual(body["detail"], "Authentication credentials were not provided.")

    def test_wrong_password(self):
        User.objects.create_user(username="e@lumora.dev", email="e@lumora.dev", password=PASSWORD)
        self.client.cookies["lang"] = "am"
        response = self.login()
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "invalid_credentials")
        self.assertEqual(response.json()["detail"], self.text("invalid_credentials", "am"))

    def test_taken_email_goes_under_its_field(self):
        User.objects.create_user(username="taken@lumora.dev", email="taken@lumora.dev")
        self.client.cookies["lang"] = "ru"
        body = self.client.post("/api/register", {"email": "Taken@Lumora.dev", "password": PASSWORD}).json()

        self.assertEqual(body["code"], "validation_error")
        self.assertEqual(body["detail"], self.text("validation_error", "ru"))
        self.assertEqual(body["email"], [self.text("email_taken", "ru")])
        self.assertEqual(body["field_codes"], {"email": ["email_taken"]})

    def test_exact_same_email_has_the_same_code(self):
        User.objects.create_user(username="taken@lumora.dev", email="taken@lumora.dev")
        body = self.client.post("/api/register", {"email": "taken@lumora.dev", "password": PASSWORD}).json()
        self.assertEqual(body["field_codes"], {"email": ["email_taken"]})

    def test_password_validators_have_codes_and_placeholders(self):
        self.client.cookies["lang"] = "am"
        body = self.client.post("/api/register", {"email": "n@lumora.dev", "password": "123"}).json()

        self.assertEqual(
            body["field_codes"]["password"],
            ["password_too_short", "password_too_common", "password_entirely_numeric"],
        )
        self.assertEqual(body["password"][0], self.text("password_too_short", "am").replace("{min_length}", "8"))

    def test_required_field(self):
        body = self.client.post("/api/register", {"email": "n@lumora.dev"}).json()
        self.assertEqual(body["field_codes"], {"password": ["required"]})
        self.assertEqual(body["password"], ["This field is required."])

    def test_bet_limits_fill_their_placeholders(self):
        game = Game.objects.get(slug="neon-crash")
        self.client.cookies["lang"] = "ru"
        response = self.play_as_a_player(str(game.max_bet + 1), "2.00")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "bet_out_of_range")
        expected = self.text("bet_out_of_range", "ru").format(min=game.min_bet, max=game.max_bet)
        self.assertEqual(response.json()["detail"], expected)

    def test_target_limits_fill_their_placeholders(self):
        self.client.cookies["lang"] = "am"
        response = self.play_as_a_player("10", "1.00")

        self.assertEqual(response.json()["code"], "target_out_of_range")
        expected = self.text("target_out_of_range", "am").format(min=MIN_TARGET, max=MAX_TARGET)
        self.assertEqual(response.json()["detail"], expected)

    def test_too_many_decimals_keeps_its_field_code(self):
        response = self.play_as_a_player("10", "1.505")
        self.assertEqual(response.json()["field_codes"], {"target": ["max_decimal_places"]})

    def test_not_enough_lc(self):
        user = User.objects.create_user(username="p@lumora.dev", email="p@lumora.dev")
        wallet = open_wallet(user)
        Game.objects.filter(slug="neon-crash").update(max_bet=wallet.balance + 1)
        self.client.force_authenticate(user)
        self.client.cookies["lang"] = "am"

        response = self.client.post("/api/crash_bets", {"amount": str(wallet.balance + 1), "target": "2.00"})

        self.assertEqual(response.json(), {"code": "not_enough_lc", "detail": self.text("not_enough_lc", "am")})

    def test_second_bonus_keeps_available_at(self):
        user = User.objects.create_user(username="p@lumora.dev", email="p@lumora.dev")
        open_wallet(user)
        self.client.force_authenticate(user)
        self.client.cookies["lang"] = "ru"
        self.client.post("/api/bonus")

        response = self.client.post("/api/bonus")

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "bonus_already_claimed")
        self.assertEqual(response.json()["detail"], self.text("bonus_already_claimed", "ru"))
        self.assertIn("available_at", response.json())
        user.wallet.refresh_from_db()
        self.assertEqual(user.wallet.balance, Decimal("15000.00"))

    def test_expired_session_is_translated(self):
        self.client.cookies["lang"] = "am"
        body = self.client.post("/api/token/refresh").json()
        self.assertEqual(body, {"code": "session_expired", "detail": self.text("session_expired", "am")})

    def test_method_not_allowed_and_not_found(self):
        self.client.cookies["lang"] = "ru"
        self.assertEqual(self.client.delete("/api/games").json()["code"], "method_not_allowed")
        self.assertEqual(self.client.get("/api/games/999999").json()["code"], "not_found")

    def test_csrf_failure_has_its_own_code(self):
        client = APIClient(enforce_csrf_checks=True)
        client.cookies["lang"] = "am"
        client.post("/api/register", {"email": "c@lumora.dev", "password": PASSWORD})

        response = client.post("/api/bonus")

        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json(), {"code": "csrf_failed", "detail": self.text("csrf_failed", "am")})
