import re
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.contrib import admin
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import RequestFactory, TestCase, override_settings
from django.urls import reverse
from rest_framework.test import APIClient

from accounts.models import LoginPageLabel, User
from crash.services import play
from errors.codes import ERROR_CODES
from errors.models import ErrorMessage
from fairness.services import rotate_seeds
from games.models import Game, LobbyPageLabel
from header.models import HeaderLabel, Logo
from wallet.services import claim_daily_bonus, open_wallet
from .fields import MAX_IMAGE_SIZE_MB
from .sample import COLLECTIONS, LANGS, load_sample, read_sample


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


def normalize(value):
    """Full media URLs -> /media/... paths, as they are in sample_db.json."""
    if isinstance(value, str) and value.startswith(settings.PUBLIC_BASE_URL + settings.MEDIA_URL):
        return value[len(settings.PUBLIC_BASE_URL) :]
    if isinstance(value, dict):
        return {key: normalize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [normalize(item) for item in value]
    return value


class ApiContractTests(TestCase):
    """The API must return exactly what base/sample_db.json contains."""

    client_class = APIClient

    @classmethod
    def setUpTestData(cls):
        cls.sample = read_sample()
        load_sample(cls.sample)

    def test_every_collection_has_an_endpoint(self):
        self.assertEqual(set(self.sample), set(COLLECTIONS))
        index = self.client.get("/api/").json()
        for name in COLLECTIONS:
            with self.subTest(name=name):
                self.assertIn(name, index)

    def test_every_endpoint_matches_the_sample_in_every_language(self):
        for name, expected in self.sample.items():
            has_lang = isinstance(expected, list) and "lang" in expected[0]
            for lang in LANGS if has_lang else [None]:
                for slash in ["", "/"]:
                    url = f"/api/{name}{slash}" + (f"?lang={lang}" if lang else "")
                    with self.subTest(url=url):
                        response = self.client.get(url)
                        self.assertEqual(response.status_code, 200)
                        rows = [row for row in expected if row["lang"] == lang] if lang else expected
                        self.assertEqual(normalize(response.json()), rows)

    def test_every_language_has_its_rows(self):
        for lang in LANGS:
            with self.subTest(lang=lang):
                self.assertEqual(len(self.client.get(f"/api/login_page_labels?lang={lang}").json()), 1)
                self.assertEqual(len(self.client.get(f"/api/error_messages?lang={lang}").json()), len(ERROR_CODES))

    def test_language_comes_from_the_query_then_the_cookie_then_english(self):
        url = "/api/login_page_labels"
        self.assertEqual(self.client.get(url).json()[0]["lang"], "en")

        self.client.cookies["lang"] = "am"
        self.assertEqual(self.client.get(url).json()[0]["lang"], "am")
        self.assertEqual(self.client.get(f"{url}?lang=ru").json()[0]["lang"], "ru")

        self.client.cookies["lang"] = "de"
        self.assertEqual(self.client.get(url).json()[0]["lang"], "en")

    def test_unknown_lang_filter_returns_an_empty_list(self):
        for name in [n for n, rows in self.sample.items() if isinstance(rows, list) and "lang" in rows[0]]:
            with self.subTest(name=name):
                response = self.client.get(f"/api/{name}?lang=de")
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json(), [])

    def test_error_messages_can_be_filtered_by_code(self):
        rows = self.client.get("/api/error_messages?lang=am&code=not_enough_lc").json()
        self.assertEqual([row["code"] for row in rows], ["not_enough_lc"])

    def test_logos_returns_one_object_with_a_full_image_url(self):
        logo = self.client.get("/api/logos").json()
        self.assertIsInstance(logo, dict)
        self.assertEqual(logo["image"], f"{settings.PUBLIC_BASE_URL}/media/images/header/logo.png")

    def test_sample_logo_file_is_in_the_repo(self):
        self.assertTrue((Path(settings.MEDIA_ROOT) / "images/header/logo.png").is_file())

    def test_languages_keep_their_order(self):
        self.assertEqual([row["code"] for row in self.client.get("/api/languages").json()], ["en", "am", "ru"])

    def test_every_error_code_has_a_text_in_every_language(self):
        self.assertEqual({row["code"] for row in self.sample["error_messages"]}, set(ERROR_CODES))
        for code in ERROR_CODES:
            for lang in LANGS:
                with self.subTest(code=code, lang=lang):
                    self.assertTrue(ErrorMessage.objects.get(code=code, lang=lang).text)

    def test_translations_keep_their_placeholders(self):
        for code in ERROR_CODES:
            with self.subTest(code=code):
                texts = ErrorMessage.objects.filter(code=code).values_list("text", flat=True)
                self.assertEqual(len({tuple(sorted(re.findall(r"\{\w+\}", text))) for text in texts}), 1)

    def test_no_label_is_empty(self):
        for model in [LoginPageLabel, LobbyPageLabel, HeaderLabel]:
            self.assertEqual(model.objects.count(), len(LANGS))
            for label in model.objects.all():
                for field in label._meta.concrete_fields:
                    with self.subTest(model=model.__name__, lang=label.lang, field=field.name):
                        self.assertTrue(getattr(label, field.attname))

    def test_lobby_placeholders_are_in_every_language(self):
        for label in LobbyPageLabel.objects.all():
            with self.subTest(lang=label.lang):
                self.assertIn("{time}", label.bonus_next)

    def test_sidebar_and_categories_have_the_same_rows_in_every_language(self):
        expected = {
            "sidebar_items": lambda row: (row["url"], row["order"], row["is_soon"]),
            "game_categories": lambda row: (row["code"], row["order"], row["is_soon"]),
        }
        for name, key in expected.items():
            rows = [{key(row) for row in self.client.get(f"/api/{name}?lang={lang}").json()} for lang in LANGS]
            with self.subTest(name=name):
                self.assertEqual(rows[0], rows[1])
                self.assertEqual(rows[0], rows[2])

    def test_every_game_category_has_names(self):
        codes = {code for code, _ in Game.Category.choices}
        for lang in LANGS:
            with self.subTest(lang=lang):
                rows = self.client.get(f"/api/game_categories?lang={lang}").json()
                self.assertEqual({row["code"] for row in rows}, codes)

    def test_content_api_is_read_only(self):
        for method in ["post", "put", "patch", "delete"]:
            for name in COLLECTIONS:
                with self.subTest(method=method, name=name):
                    response = getattr(self.client, method)(f"/api/{name}")
                    self.assertEqual(response.status_code, 405)
        self.assertEqual(LoginPageLabel.objects.count(), len(self.sample["login_page_labels"]))


class LoadSampleTests(TestCase):
    def test_it_can_run_twice_and_replaces_content(self):
        call_command("load_sample", stdout=StringIO())
        ErrorMessage.objects.filter(code="not_found").update(text="Edited")
        call_command("load_sample", stdout=StringIO())

        self.assertEqual(ErrorMessage.objects.count(), len(read_sample()["error_messages"]))
        self.assertFalse(ErrorMessage.objects.filter(text="Edited").exists())
        self.assertEqual(ErrorMessage.objects.order_by("id").first().id, 1)

    def test_it_never_touches_players(self):
        user = User.objects.create_user(username="s@lumora.dev", email="s@lumora.dev")
        wallet = open_wallet(user)
        balance = wallet.balance
        call_command("load_sample", stdout=StringIO())
        wallet.refresh_from_db()
        self.assertEqual(wallet.balance, balance)


PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89"
    b"\x00\x00\x00\rIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82"
)


class AdminUploadTests(TestCase):
    """Images are uploaded through /admin/ and come back from the API as full URLs."""

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
        self.client.force_login(User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev"))

    def add_logo(self, name, content, content_type="image/png"):
        upload = SimpleUploadedFile(name, content, content_type=content_type)
        return self.client.post(reverse("admin:header_logo_add"), {"name": "Lumora", "image": upload})

    def test_admin_upload_is_returned_by_the_api(self):
        response = self.add_logo("new-logo.png", PNG)
        self.assertEqual(response.status_code, 302)
        image = Logo.objects.get().image
        self.assertTrue(image.name.startswith("images/header/new-logo"))
        self.assertTrue(image.storage.exists(image.name))

        logo = self.client.get("/api/logos").json()
        self.assertEqual(logo["image"], f"{settings.PUBLIC_BASE_URL}/media/{image.name}")

    def test_the_site_has_one_logo(self):
        self.add_logo("new-logo.png", PNG)
        self.assertEqual(self.client.get(reverse("admin:header_logo_add")).status_code, 403)

    def test_real_images_of_every_allowed_format_are_accepted(self):
        for name, content in [
            ("a.png", PNG),
            ("a.jpg", b"\xff\xd8\xff\xe0" + b"0" * 16),
            ("a.gif", b"GIF89a" + b"0" * 16),
            ("a.webp", b"RIFF\x00\x00\x00\x00WEBP" + b"0" * 16),
        ]:
            with self.subTest(name=name):
                Logo.objects.all().delete()
                self.assertEqual(self.add_logo(name, content).status_code, 302)

    def test_admin_rejects_files_that_are_not_images(self):
        for name, content, content_type in [
            ("evil.html", b"<script>alert(1)</script>", "text/html"),
            ("evil.png", b"this is not an image at all", "image/png"),
            ("evil.jpg", b"<script>alert(1)</script>", "image/jpeg"),
            ("logo.svg", b"<svg xmlns='http://www.w3.org/2000/svg'><script>alert(1)</script></svg>", "image/svg+xml"),
        ]:
            with self.subTest(name=name):
                response = self.add_logo(name, content, content_type)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Logo.objects.exists())

    def test_admin_rejects_images_over_the_size_limit(self):
        response = self.add_logo("big.png", PNG + b"0" * (MAX_IMAGE_SIZE_MB * 1024 * 1024))
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Logo.objects.exists())

    def test_new_models_can_be_filtered_by_language_in_the_admin(self):
        load_sample(read_sample())
        for url in ["admin:errors_errormessage_changelist", "admin:accounts_loginpagelabel_changelist"]:
            with self.subTest(url=url):
                response = self.client.get(reverse(url), {"lang__exact": "am"})
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["cl"].result_list)


class AdminTests(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser("admin@lumora.dev", "admin@lumora.dev")
        self.client.force_login(self.admin)
        # one row of everything, so change pages have something to open
        load_sample(read_sample())
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
