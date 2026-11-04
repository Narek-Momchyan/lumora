from django.test import TestCase

from base.sample import load_sample, read_sample


class SportsPageLabelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        load_sample(read_sample())

    def test_labels_are_public_and_filtered_by_lang(self):
        for lang in ["en", "am", "ru"]:
            with self.subTest(lang=lang):
                rows = self.client.get(f"/api/sports_page_labels?lang={lang}").json()
                self.assertEqual([row["lang"] for row in rows], [lang])
