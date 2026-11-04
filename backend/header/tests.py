from pathlib import Path

from django.conf import settings
from django.core.exceptions import ValidationError
from django.test import TestCase

from base.sample import read_sample
from games.models import Game
from .models import SidebarItem, category_url


class LogoTests(TestCase):
    def test_logos_is_an_empty_object_before_a_logo_is_added(self):
        response = self.client.get("/api/logos")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})


class SidebarItemTests(TestCase):
    def test_a_category_item_must_open_the_lobby_filtered_by_it(self):
        item = SidebarItem(lang="en", mode="casino", title="Slots", url="/slots", category=Game.Category.SLOT)
        with self.assertRaises(ValidationError):
            item.full_clean()

        item.url = "/casino?category=slot"
        item.full_clean()

    def test_only_a_casino_item_has_a_category(self):
        item = SidebarItem(lang="en", mode="sports", title="Slots", url="/casino?category=slot", category="slot")
        with self.assertRaises(ValidationError):
            item.full_clean()

    def test_every_sample_category_item_opens_its_category(self):
        for row in read_sample()["sidebar_items"]:
            if row["category"]:
                with self.subTest(row=row):
                    self.assertEqual(row["url"], category_url(row["category"]))

    def test_every_sample_icon_is_in_the_repo(self):
        for row in read_sample()["sidebar_items"]:
            with self.subTest(icon=row["icon"]):
                path = Path(settings.MEDIA_ROOT) / row["icon"].removeprefix(settings.MEDIA_URL)
                self.assertTrue(path.is_file())
