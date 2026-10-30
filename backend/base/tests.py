from django.contrib import admin
from django.test import RequestFactory, TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import User
from crash.services import play
from fairness.services import rotate_seeds
from wallet.services import claim_daily_bonus, open_wallet


class ApiRulesTests(TestCase):
    """Rules shared by every endpoint (same as in Fruit Food)."""

    client_class = APIClient

    def setUp(self):
        self.user = User.objects.create_user(username="r@lumora.dev", email="r@lumora.dev")
        self.client.force_authenticate(self.user)

    def test_every_endpoint_works_with_and_without_a_trailing_slash(self):
        for name in ["games", "leaderboard", "me", "wallet", "transactions", "seeds", "crash_bets"]:
            for slash in ["", "/"]:
                url = f"/api/{name}{slash}"
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_lists_are_plain_arrays_and_single_objects_are_objects(self):
        for name in ["games", "leaderboard", "transactions", "seeds", "crash_bets"]:
            with self.subTest(name=name):
                self.assertIsInstance(self.client.get(f"/api/{name}").json(), list)
        for name in ["me", "wallet"]:
            with self.subTest(name=name):
                self.assertIsInstance(self.client.get(f"/api/{name}").json(), dict)

    def test_api_index_is_public_and_private_data_is_not(self):
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get("/api/").status_code, 200)
        for name in ["me", "wallet", "transactions", "seeds", "crash_bets"]:
            with self.subTest(name=name):
                self.assertEqual(self.client.get(f"/api/{name}").status_code, 401)

    def test_cors_allows_the_frontend_only(self):
        allowed = self.client.get("/api/games", HTTP_ORIGIN="http://localhost:3000")
        self.assertEqual(allowed.get("Access-Control-Allow-Origin"), "http://localhost:3000")

        other = self.client.get("/api/games", HTTP_ORIGIN="https://evil.example")
        self.assertIsNone(other.get("Access-Control-Allow-Origin"))


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev")
        self.client.force_login(self.admin)
        # one row of everything, so change pages have something to open
        wallet = open_wallet(self.admin)
        claim_daily_bonus(wallet)
        play(self.admin, "10", "2.00")
        rotate_seeds(self.admin)

    def test_every_admin_page_opens(self):
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        for model, model_admin in admin.site._registry.items():
            info = (model._meta.app_label, model._meta.model_name)
            urls = [reverse("admin:%s_%s_changelist" % info)]
            if model_admin.has_add_permission(request):
                urls.append(reverse("admin:%s_%s_add" % info))
            obj = model.objects.first()
            if obj is not None:
                urls.append(reverse("admin:%s_%s_change" % info, args=[obj.pk]))
            for url in urls:
                with self.subTest(url=url):
                    self.assertEqual(self.client.get(url).status_code, 200)

    def test_money_and_history_are_read_only_in_the_admin(self):
        request = RequestFactory().get("/admin/")
        request.user = self.admin
        for model_name in ["wallet", "transaction", "seedpair", "crashbet"]:
            model_admin = next(a for m, a in admin.site._registry.items() if m._meta.model_name == model_name)
            with self.subTest(model=model_name):
                self.assertFalse(model_admin.has_add_permission(request))
                self.assertFalse(model_admin.has_change_permission(request))
