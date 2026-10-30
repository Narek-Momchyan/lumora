from decimal import Decimal

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from .models import User

PASSWORD = "Neon-Crash-2026"


@override_settings(PASSWORD_HASHERS=["django.contrib.auth.hashers.MD5PasswordHasher"])  # fast, tests only
class AuthTests(TestCase):
    """Register, log in with a JWT, read /api/me."""

    client_class = APIClient

    def register(self, email="narek@lumora.dev", password=PASSWORD, **extra):
        return self.client.post("/api/register", {"email": email, "password": password, **extra})

    def login(self, email="narek@lumora.dev", password=PASSWORD):
        return self.client.post("/api/token", {"email": email, "password": password})

    def test_register_opens_wallet_with_signup_grant(self):
        response = self.register(display_name="Narek")
        self.assertEqual(response.status_code, 201)
        user = User.objects.get(email="narek@lumora.dev")
        self.assertEqual(response.json(), {"id": user.id, "email": "narek@lumora.dev", "display_name": "Narek"})
        self.assertEqual(user.wallet.balance, Decimal("10000.00"))

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
        self.assertFalse(User.objects.exists())

    def test_login_with_any_letter_case_and_read_me(self):
        self.register()
        tokens = self.login(email="Narek@Lumora.DEV").json()
        self.assertIn("refresh", tokens)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['access']}")
        me = self.client.get("/api/me").json()
        self.assertEqual(me["email"], "narek@lumora.dev")

    def test_wrong_password_is_401(self):
        self.register()
        self.assertEqual(self.login(password="wrong-password").status_code, 401)

    def test_refresh_gives_a_new_access_token(self):
        self.register()
        refresh = self.login().json()["refresh"]
        response = self.client.post("/api/token/refresh", {"refresh": refresh})
        self.assertEqual(response.status_code, 200)
        self.assertIn("access", response.json())

    def test_me_requires_a_token(self):
        self.assertEqual(self.client.get("/api/me").status_code, 401)
