from itertools import islice
from statistics import mean

from django.test import SimpleTestCase, TestCase
from rest_framework.test import APIClient

from accounts.models import User
from . import rng, services
from .models import SeedPair


class RngTests(SimpleTestCase):
    def test_same_inputs_give_the_same_results(self):
        first = list(islice(rng.float_stream("seed", "client", 7), 10))
        again = list(islice(rng.float_stream("seed", "client", 7), 10))
        self.assertEqual(first, again)

    def test_another_nonce_gives_another_result(self):
        self.assertNotEqual(rng.first_float("seed", "client", 1), rng.first_float("seed", "client", 2))

    def test_floats_are_in_range_and_roughly_uniform(self):
        values = [rng.first_float("seed", "client", n) for n in range(20_000)]
        self.assertTrue(all(0 <= v < 1 for v in values))
        self.assertAlmostEqual(mean(values), 0.5, delta=0.01)

    def test_hash_commits_to_the_seed(self):
        seed = rng.new_server_seed()
        self.assertEqual(len(seed), 64)
        self.assertEqual(rng.hash_seed(seed), rng.hash_seed(seed))
        self.assertNotEqual(rng.hash_seed(seed), rng.hash_seed(seed + "x"))


class SeedApiTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.user = User.objects.create_user(username="s@lumora.dev", email="s@lumora.dev")
        self.client.force_authenticate(self.user)

    def test_first_visit_creates_an_active_pair_without_the_secret(self):
        pairs = self.client.get("/api/seeds").json()
        self.assertEqual(len(pairs), 1)
        self.assertTrue(pairs[0]["is_active"])
        self.assertIsNone(pairs[0]["server_seed"])
        self.assertEqual(len(pairs[0]["server_seed_hash"]), 64)

    def test_nonces_count_up(self):
        self.assertEqual(services.next_nonce(self.user)[1], 0)
        self.assertEqual(services.next_nonce(self.user)[1], 1)
        self.assertEqual(SeedPair.objects.get(user=self.user, is_active=True).nonce, 2)

    def test_rotation_reveals_the_old_seed_and_starts_a_new_pair(self):
        old_hash = self.client.get("/api/seeds").json()[0]["server_seed_hash"]
        response = self.client.post("/api/seeds", {"client_seed": "my-lucky-seed"})
        self.assertEqual(response.status_code, 201)
        revealed, active = response.json()["revealed"], response.json()["active"]
        self.assertEqual(rng.hash_seed(revealed["server_seed"]), old_hash)
        self.assertFalse(revealed["is_active"])
        self.assertEqual(active["client_seed"], "my-lucky-seed")
        self.assertIsNone(active["server_seed"])
        self.assertEqual(active["nonce"], 0)
        self.assertEqual([p["is_active"] for p in self.client.get("/api/seeds").json()], [True, False])

    def test_bad_client_seed_is_rejected(self):
        response = self.client.post("/api/seeds", {"client_seed": "has spaces!"})
        self.assertEqual(response.status_code, 400)
        self.assertIn("client_seed", response.json())

    def test_players_see_only_their_own_seeds(self):
        other = User.objects.create_user(username="o@lumora.dev", email="o@lumora.dev")
        services.rotate_seeds(other)
        self.assertEqual(len(self.client.get("/api/seeds").json()), 1)
