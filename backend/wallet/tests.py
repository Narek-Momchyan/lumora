import threading
from datetime import timedelta
from decimal import Decimal

from django.db import connection
from django.db.models import Sum
from django.test import TestCase, TransactionTestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import User
from . import services
from .models import Transaction


def make_wallet(email="player@lumora.dev"):
    user = User.objects.create_user(username=email, email=email)
    return services.open_wallet(user)


def ledger_sum(wallet):
    return wallet.transactions.aggregate(total=Sum("amount"))["total"]


class WalletServiceTests(TestCase):
    """Money rules: signup grant, bets, wins, limits, idempotency, daily bonus."""

    def setUp(self):
        self.wallet = make_wallet()

    def test_new_wallet_gets_signup_grant(self):
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))
        self.assertEqual(self.wallet.transactions.get().kind, Transaction.Kind.SIGNUP)

    def test_open_wallet_twice_gives_the_same_wallet(self):
        again = services.open_wallet(self.wallet.user)
        self.assertEqual(again.pk, self.wallet.pk)
        self.assertEqual(self.wallet.transactions.count(), 1)

    def test_bet_and_win_update_balance_and_ledger(self):
        services.debit(self.wallet, "100", game="neon-crash", round_id="r1")
        services.credit(self.wallet, "247", game="neon-crash", round_id="r1")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10147.00"))
        self.assertEqual(ledger_sum(self.wallet), self.wallet.balance)

    def test_cannot_bet_more_than_the_balance(self):
        with self.assertRaises(services.InsufficientFunds):
            services.debit(self.wallet, "10000.01", game="neon-crash")
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("10000.00"))
        self.assertEqual(self.wallet.transactions.count(), 1)

    def test_rejects_zero_negative_and_sub_cent_amounts(self):
        for bad in ["0", "-5", "0.001"]:
            with self.subTest(amount=bad), self.assertRaises(services.WalletError):
                services.debit(self.wallet, bad, game="neon-crash")

    def test_same_idempotency_key_charges_once(self):
        first = services.debit(self.wallet, "50", game="zeus-legacy", idempotency_key="spin-1")
        second = services.debit(self.wallet, "50", game="zeus-legacy", idempotency_key="spin-1")
        self.wallet.refresh_from_db()
        self.assertEqual(first.pk, second.pk)
        self.assertEqual(self.wallet.balance, Decimal("9950.00"))

    def test_daily_bonus_once_per_24_hours(self):
        now = timezone.now()
        services.claim_daily_bonus(self.wallet, now=now)
        with self.assertRaises(services.BonusNotReady):
            services.claim_daily_bonus(self.wallet, now=now + timedelta(hours=23))
        services.claim_daily_bonus(self.wallet, now=now + timedelta(hours=24))
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("20000.00"))
        self.assertEqual(ledger_sum(self.wallet), self.wallet.balance)

    def test_ledger_matches_balance_after_many_operations(self):
        for i in range(50):
            services.debit(self.wallet, "10", game="volt-mines", round_id=str(i))
            if i % 3 == 0:
                services.credit(self.wallet, "25.50", game="volt-mines", round_id=str(i))
        self.wallet.refresh_from_db()
        self.assertEqual(ledger_sum(self.wallet), self.wallet.balance)
        self.assertEqual(self.wallet.transactions.first().balance_after, self.wallet.balance)


class WalletApiTests(TestCase):
    client_class = APIClient

    def setUp(self):
        self.wallet = make_wallet()
        self.client.force_authenticate(self.wallet.user)

    def test_wallet_needs_a_token(self):
        self.client.force_authenticate(None)
        for url in ["/api/wallet", "/api/transactions", "/api/bonus"]:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 401)

    def test_wallet_is_a_single_object(self):
        data = self.client.get("/api/wallet").json()
        self.assertEqual(data["balance"], "10000.00")
        self.assertIsNone(data["bonus_available_at"])

    def test_transactions_are_a_plain_list_of_own_rows(self):
        other = make_wallet("other@lumora.dev")
        services.debit(other, "10", game="neon-crash")
        services.debit(self.wallet, "10", game="neon-crash")
        rows = self.client.get("/api/transactions").json()
        self.assertEqual([r["kind"] for r in rows], ["bet", "signup"])
        self.assertEqual(rows[0]["amount"], "-10.00")

    def test_transactions_filters(self):
        services.debit(self.wallet, "10", game="neon-crash")
        services.debit(self.wallet, "10", game="zeus-legacy")
        self.assertEqual(len(self.client.get("/api/transactions?kind=bet").json()), 2)
        self.assertEqual(len(self.client.get("/api/transactions?game=zeus-legacy").json()), 1)
        self.assertEqual(self.client.get("/api/transactions?game=does-not-exist").json(), [])

    def test_transactions_list_is_limited_to_100(self):
        for i in range(110):
            services.debit(self.wallet, "1", game="neon-crash", round_id=str(i))
        self.assertEqual(len(self.client.get("/api/transactions").json()), 100)

    def test_daily_bonus(self):
        response = self.client.post("/api/bonus")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()["amount"], "5000.00")
        wallet = self.client.get("/api/wallet").json()
        self.assertEqual(wallet["balance"], "15000.00")
        self.assertIsNotNone(wallet["bonus_available_at"])

        again = self.client.post("/api/bonus")
        self.assertEqual(again.status_code, 409)
        self.assertIn("available_at", again.json())


class WalletConcurrencyTests(TransactionTestCase):
    """Real parallel requests on PostgreSQL: row locks must keep the balance right."""

    def setUp(self):
        self.wallet = make_wallet("race@lumora.dev")

    def run_in_threads(self, count, func):
        barrier = threading.Barrier(count)
        results = []
        lock = threading.Lock()

        def worker(i):
            try:
                barrier.wait()
                result = func(i)
            except Exception as exc:
                result = exc
            finally:
                connection.close()  # every thread has its own database connection
            with lock:
                results.append(result)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(count)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        return results

    def test_parallel_bets_never_spend_more_than_the_balance(self):
        # 30 bets of 500 LC at the same moment on a 10,000 LC wallet: exactly 20 can succeed.
        results = self.run_in_threads(
            30, lambda i: services.debit(self.wallet, "500", game="neon-crash", round_id=f"race-{i}")
        )
        self.assertEqual(sum(isinstance(r, Transaction) for r in results), 20)
        self.assertEqual(sum(isinstance(r, services.InsufficientFunds) for r in results), 10)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("0.00"))
        self.assertEqual(ledger_sum(self.wallet), self.wallet.balance)

    def test_parallel_retries_with_the_same_key_charge_once(self):
        results = self.run_in_threads(
            10, lambda i: services.debit(self.wallet, "50", game="zeus-legacy", idempotency_key="spin-1")
        )
        self.assertTrue(all(isinstance(r, Transaction) for r in results), results)
        self.assertEqual(len({r.pk for r in results}), 1)
        self.wallet.refresh_from_db()
        self.assertEqual(self.wallet.balance, Decimal("9950.00"))
