from decimal import Decimal

from django.conf import settings
from django.db import models


class Wallet(models.Model):
    """One per player. The balance changes only through wallet.services (see CLAUDE.md)."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, related_name="wallet", on_delete=models.CASCADE)
    balance = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    last_bonus_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Wallets"
        ordering = ["id"]
        constraints = [
            models.CheckConstraint(condition=models.Q(balance__gte=0), name="wallet_balance_non_negative"),
        ]

    def __str__(self):
        return f"{self.user} · {self.balance} LC"


class Transaction(models.Model):
    """Append-only ledger. amount is signed: negative = bet, positive = win / bonus / signup.

    The sum of a wallet's transactions always equals its balance (tested).
    """

    class Kind(models.TextChoices):
        SIGNUP = "signup", "Signup grant"
        BONUS = "bonus", "Daily bonus"
        BET = "bet", "Bet"
        WIN = "win", "Win"
        JACKPOT = "jackpot", "Jackpot"

    wallet = models.ForeignKey(Wallet, related_name="transactions", on_delete=models.CASCADE)
    kind = models.CharField(max_length=16, choices=Kind.choices)
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    game = models.CharField(max_length=40, blank=True)
    round_id = models.CharField(max_length=64, blank=True)
    idempotency_key = models.CharField(max_length=64, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Transactions"
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["wallet", "idempotency_key"],
                condition=models.Q(idempotency_key__isnull=False),
                name="unique_wallet_idempotency_key",
            ),
        ]
        indexes = [models.Index(fields=["wallet", "-created_at"], name="transaction_wallet_created")]

    def __str__(self):
        return f"{self.kind} {self.amount} LC"


class JackpotPool(models.Model):
    """A progressive jackpot shared by all players. Changes only through wallet.services.

    Six decimals, because a pool grows by a tiny share of every stake.
    """

    tier = models.CharField(max_length=8)
    amount = models.DecimalField(max_digits=16, decimal_places=6)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Jackpot pools"
        ordering = ["amount"]
        constraints = [
            models.UniqueConstraint(fields=["tier"], name="unique_jackpot_pool_tier"),
        ]

    def __str__(self):
        return f"{self.tier} · {self.amount} LC"
