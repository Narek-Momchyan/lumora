from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from .models import User

PASSWORD = "Neon-Crash-2026"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])  # fast, tests only
class AuthTests(TestCase):
    """Register, log in with cookies, read /api/me."""

    client_class = APIClient

    def register(self, email="narek@lumora.dev", password=PASSWORD, **extra):
        return self.client.post("/api/register", {"email": email, "password": password, **extra})

    def login(self, email="narek@lumora.dev", password=PASSWORD):
        return self.client.post("/api/token", {"email": email, "password": password})

    def test_register_opens_wallet_with_signup_grant(self):
        response = self.register(display_name="Narek")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="narek@lumora.dev")
        body = response.json()
        self.assertEqual(body["id"], user.id)
        self.assertEqual(body["email"], "narek@lumora.dev")
        self.assertEqual(body["display_name"], "Narek")
        self.assertIn("date_joined", body)
        self.assertEqual(user.wallet.balance, Decimal("10000.00"))

    def test_register_logs_the_player_in(self):
        self.assertIn(settings.AUTH_ACCESS_COOKIE, self.register().cookies)
        self.assertEqual(self.client.get("/api/me").json()["email"], "narek@lumora.dev")

    def test_email_is_saved_in_lowercase_and_unique_in_any_case(self):
        self.register(email="Narek@Lumora.dev")
        self.assertTrue(User.objects.filter(email="narek@lumora.dev").exists())
        response = self.register(email="NAREK@lumora.dev")
        self.assertEqual(response.status_code, 400)
        self.assertIn("email", response.json())

    def test_weak_password_is_rejected(self):
        response = self.register(password="12345")
        self.assertEqual(response.status_code, 400)
        self.assertIn("password", response.json())
        self.assertNotIn(settings.AUTH_ACCESS_COOKIE, response.cookies)
        self.assertFalse(User.objects.exists())

    def test_login_with_any_letter_case_and_read_me(self):
        self.register()
        self.client.cookies.clear()
        self.assertEqual(self.login(email="Narek@Lumora.DEV").status_code, 200)
        me = self.client.get("/api/me").json()
        self.assertEqual(me["email"], "narek@lumora.dev")

    def test_login_sets_http_only_cookies_and_returns_the_player(self):
        self.register()
        self.client.cookies.clear()
        response = self.login()

        self.assertEqual(response.json(), self.client.get("/api/me").json())
        for name in [settings.AUTH_ACCESS_COOKIE, settings.AUTH_REFRESH_COOKIE]:
            with self.subTest(cookie=name):
                self.assertTrue(response.cookies[name]["httponly"])
                self.assertEqual(response.cookies[name]["samesite"], "Lax")
        self.assertIn(settings.CSRF_COOKIE_NAME, response.cookies)
        self.assertFalse(response.cookies[settings.CSRF_COOKIE_NAME]["httponly"])

    def test_cookie_lifetimes_match_the_tokens(self):
        response = self.register()
        self.assertEqual(response.cookies[settings.AUTH_ACCESS_COOKIE]["max-age"], 30 * 60)
        self.assertEqual(response.cookies[settings.AUTH_REFRESH_COOKIE]["max-age"], 7 * 24 * 60 * 60)

    def test_tokens_are_not_in_the_body(self):
        self.register()
        body = self.login().json()
        self.assertNotIn("access", body)
        self.assertNotIn("refresh", body)

    @override_settings(AUTH_COOKIE_SECURE=True)
    def test_cookies_are_secure_when_the_setting_is_on(self):
        response = self.register()
        self.assertTrue(response.cookies[settings.AUTH_ACCESS_COOKIE]["secure"])
        self.assertTrue(response.cookies[settings.AUTH_REFRESH_COOKIE]["secure"])

    @override_settings(AUTH_COOKIE_SECURE=False)
    def test_cookies_are_not_secure_when_the_setting_is_off(self):
        response = self.register()
        self.assertFalse(response.cookies[settings.AUTH_ACCESS_COOKIE]["secure"])

    def test_wrong_password_is_401(self):
        self.register()
        self.client.cookies.clear()
        response = self.login(password="wrong-password")
        self.assertEqual(response.status_code, 401)
        self.assertNotIn(settings.AUTH_ACCESS_COOKIE, response.cookies)

    def test_login_works_with_an_expired_access_cookie(self):
        self.register()
        token = AccessToken.for_user(User.objects.get())
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies[settings.AUTH_ACCESS_COOKIE] = str(token)
        self.assertEqual(self.login().status_code, 200)

    def test_me_requires_a_cookie(self):
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_a_bearer_header_is_not_accepted(self):
        user = User.objects.create_user(username="b@lumora.dev", email="b@lumora.dev")
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {AccessToken.for_user(user)}")
        self.assertEqual(self.client.get("/api/me").status_code, 401)

    def test_expired_cookie_is_401_on_private_and_ignored_on_public_endpoints(self):
        user = User.objects.create_user(username="e@lumora.dev", email="e@lumora.dev")
        token = AccessToken.for_user(user)
        token.set_exp(lifetime=-timedelta(seconds=1))
        self.client.cookies[settings.AUTH_ACCESS_COOKIE] = str(token)

        self.assertEqual(self.client.get("/api/me").status_code, 401)
        self.assertEqual(self.client.get("/api/games").status_code, 200)

    def test_refresh_sets_a_new_access_cookie_from_the_refresh_cookie(self):
        self.register()
        del self.client.cookies[settings.AUTH_ACCESS_COOKIE]
        self.assertEqual(self.client.get("/api/me").status_code, 401)

        response = self.client.post("/api/token/refresh")

        self.assertEqual(response.status_code, 204)
        self.assertTrue(response.cookies[settings.AUTH_ACCESS_COOKIE]["httponly"])
        self.assertNotIn(settings.AUTH_REFRESH_COOKIE, response.cookies)
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_refresh_ignores_a_refresh_token_in_the_body(self):
        user = User.objects.create_user(username="f@lumora.dev", email="f@lumora.dev")
        response = self.client.post("/api/token/refresh", {"refresh": str(RefreshToken.for_user(user))})
        self.assertEqual(response.status_code, 401)

    def test_refresh_without_a_cookie_is_401(self):
        self.assertEqual(self.client.post("/api/token/refresh").status_code, 401)

    def test_refresh_with_a_bad_cookie_is_401_and_clears_the_cookies(self):
        self.client.cookies[settings.AUTH_REFRESH_COOKIE] = "not-a-token"
        response = self.client.post("/api/token/refresh")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.cookies[settings.AUTH_REFRESH_COOKIE]["max-age"], 0)

    def test_refresh_for_a_deleted_player_is_401(self):
        user = User.objects.create_user(username="g@lumora.dev", email="g@lumora.dev")
        self.client.cookies[settings.AUTH_REFRESH_COOKIE] = str(RefreshToken.for_user(user))
        user.delete()
        self.assertEqual(self.client.post("/api/token/refresh").status_code, 401)

    def test_logout_deletes_the_cookies(self):
        self.register()
        response = self.client.post("/api/logout")

        self.assertEqual(response.status_code, 204)
        for name in [settings.AUTH_ACCESS_COOKIE, settings.AUTH_REFRESH_COOKIE]:
            with self.subTest(cookie=name):
                self.assertEqual(response.cookies[name]["max-age"], 0)
        self.assertEqual(self.client.get("/api/me").status_code, 401)
        self.assertEqual(self.client.post("/api/token/refresh").status_code, 401)


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])  # fast, tests only
class CsrfTests(TestCase):
    """The default test client skips CSRF checks, so this one turns them on."""

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        response = self.client.post("/api/register", {"email": "csrf@lumora.dev", "password": PASSWORD})
        self.assertEqual(response.status_code, 201)
        self.csrf = response.cookies[settings.CSRF_COOKIE_NAME].value
        self.user = User.objects.get()

    def test_login_and_register_need_no_csrf_token(self):
        self.client.cookies.clear()
        response = self.client.post("/api/token", {"email": "csrf@lumora.dev", "password": PASSWORD})
        self.assertEqual(response.status_code, 200)

    def test_get_needs_no_csrf_header(self):
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_post_without_the_csrf_header_is_rejected_and_nothing_changes(self):
        response = self.client.post("/api/bonus")
        self.assertEqual(response.status_code, 403)
        self.assertIn("CSRF", response.json()["detail"])
        self.user.wallet.refresh_from_db()
        self.assertEqual(self.user.wallet.balance, Decimal("10000.00"))

    def test_post_with_a_wrong_csrf_header_is_rejected(self):
        self.assertEqual(self.client.post("/api/bonus", HTTP_X_CSRFTOKEN="wrong").status_code, 403)

    def test_post_with_the_csrf_header_works(self):
        response = self.client.post("/api/bonus", HTTP_X_CSRFTOKEN=self.csrf)
        self.assertEqual(response.status_code, 201)

    def test_post_from_the_next_app_origin_works(self):
        response = self.client.post("/api/bonus", HTTP_X_CSRFTOKEN=self.csrf, HTTP_ORIGIN="http://localhost:3000")
        self.assertEqual(response.status_code, 201)

    def test_post_from_another_origin_is_rejected(self):
        response = self.client.post("/api/bonus", HTTP_X_CSRFTOKEN=self.csrf, HTTP_ORIGIN="https://evil.example")
        self.assertEqual(response.status_code, 403)

    def test_refresh_and_logout_need_the_csrf_header(self):
        for url in ["/api/token/refresh", "/api/logout"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url).status_code, 403)
        self.assertEqual(self.client.get("/api/me").status_code, 200)

    def test_refresh_and_logout_work_with_the_csrf_header(self):
        for url in ["/api/token/refresh", "/api/logout"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.post(url, HTTP_X_CSRFTOKEN=self.csrf).status_code, 204)


class PublicIdTests(TestCase):
    def test_me_has_a_public_id_that_is_not_the_id(self):
        user = User.objects.create_user(username="me@lumora.dev", email="me@lumora.dev")
        client = APIClient()
        client.force_authenticate(user)
        me = client.get("/api/me").json()
        self.assertRegex(me["public_id"], r"^[0-9a-f]{12}$")
        self.assertNotEqual(me["public_id"], str(me["id"]))


class DisplayNameAtSignTests(TestCase):
    """A display name is shown to other players, so it can never contain an @ (an email address)."""

    client_class = APIClient

    @classmethod
    def setUpTestData(cls):
        from base.sample import load_sample, read_sample

        load_sample(read_sample())

    def register(self, display_name, email="new@lumora.dev"):
        return self.client.post("/api/register", {"email": email, "password": PASSWORD, "display_name": display_name})

    def test_a_name_with_an_at_sign_is_refused_with_a_code_in_every_language(self):
        for lang, text in (("en", "cannot contain the @"), ("am", "@ նշանը"), ("ru", "знак @")):
            self.client.cookies["lang"] = lang
            response = self.register("me@lumora.dev", email=f"{lang}@lumora.dev")
            self.assertEqual(response.status_code, 400)
            self.assertEqual(response.json()["field_codes"]["display_name"], ["display_name_has_at"])
            self.assertIn(text, response.json()["display_name"][0])
        self.assertEqual(User.objects.count(), 0)

    def test_look_alike_at_signs_are_refused_too(self):
        for name in ["me＠lumora.dev", "me﹫lumora", "@", "a@"]:
            with self.subTest(name=name):
                self.assertEqual(self.register(name).status_code, 400)

    def test_ordinary_names_still_work(self):
        for index, name in enumerate(["Narek", "Նարեկ", "Нарек", "kite_88", ""]):
            with self.subTest(name=name):
                self.assertEqual(self.register(name, email=f"ok{index}@lumora.dev").status_code, 201)

    def test_the_admin_form_and_full_clean_refuse_it_as_well(self):
        from django.core.exceptions import ValidationError

        with self.assertRaises(ValidationError) as caught:
            User(email="x@lumora.dev", username="x", display_name="a@b.c").clean_fields(exclude=["password"])
        self.assertEqual(caught.exception.error_dict["display_name"][0].code, "display_name_has_at")

    def test_the_migration_clears_existing_names_with_an_at_sign_and_keeps_the_rest(self):
        import importlib

        from django.apps import apps

        bad = User.objects.create_user(username="bad@lumora.dev", email="bad@lumora.dev", display_name="bad@lumora.dev")
        good = User.objects.create_user(username="good@lumora.dev", email="good@lumora.dev", display_name="Good")
        importlib.import_module("accounts.migrations.0004_display_name_no_at").clear_names_with_at(apps, None)
        bad.refresh_from_db()
        good.refresh_from_db()
        self.assertEqual((bad.display_name, good.display_name), ("", "Good"))
