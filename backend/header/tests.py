from django.test import TestCase


class LogoTests(TestCase):
    def test_logos_is_an_empty_object_before_a_logo_is_added(self):
        response = self.client.get("/api/logos")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})
