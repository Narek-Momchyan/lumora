"""The only place that changes balances. Games call debit() and credit(), nothing else.

Every change locks the wallet row (select_for_update) inside transaction.atomic, so two
requests at the same moment cannot spend the same coins. Passing an idempotency_key makes
a retried request return the original Transaction instead of charging or paying twice.
"""

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from base.constants import DAILY_BONUS, DAILY_BONUS_COOLDOWN, SIGNUP_BONUS
from .models import Transaction, Wallet

CENT = Decimal("0.01")


class WalletError(Exception):
    pass


class InsufficientFunds(WalletError):
    pass


class BonusNotReady(WalletError):
    def __init__(self, available_at):
        self.available_at = available_at
        super().__init__(f"Daily bonus available at {available_at.isoformat()}")


def _money(value):
    amount = Decimal(str(value)).quantize(CENT)
    if amount <= 0:
        raise WalletError("Amount must be positive")
    return amount


def _apply(wallet_id, kind, signed_amount, *, game="", round_id="", idempotency_key=None):
    with transaction.atomic():
        wallet = Wallet.objects.select_for_update().get(pk=wallet_id)
        if idempotency_key:
            # A retry with the same key waited for the lock above, so it finds the first row here.
            existing = wallet.transactions.filter(idempotency_key=idempotency_key).first()
            if existing:
                return existing
        new_balance = wallet.balance + signed_amount
        if new_balance < 0:
            raise InsufficientFunds(f"Balance {wallet.balance} is less than {-signed_amount}")
        wallet.balance = new_balance
        wallet.save(update_fields=["balance", "updated_at"])
        return Transaction.objects.create(
            wallet=wallet,
            kind=kind,
            amount=signed_amount,
            balance_after=new_balance,
            game=game,
            round_id=round_id,
            idempotency_key=idempotency_key,
        )


def open_wallet(user):
    """Return the player's wallet. The first call creates it with the signup grant."""
    with transaction.atomic():
        wallet, created = Wallet.objects.get_or_create(user=user)
        if created:
            _apply(wallet.id, Transaction.Kind.SIGNUP, SIGNUP_BONUS)
            wallet.refresh_from_db()
        return wallet


def debit(wallet, amount, *, game, round_id="", idempotency_key=None):
    """Take a bet. Raises InsufficientFunds."""
    return _apply(
        wallet.id,
        Transaction.Kind.BET,
        -_money(amount),
        game=game,
        round_id=round_id,
        idempotency_key=idempotency_key,
    )


def credit(wallet, amount, *, game, round_id="", idempotency_key=None):
    """Pay a win."""
    return _apply(
        wallet.id,
        Transaction.Kind.WIN,
        _money(amount),
        game=game,
        round_id=round_id,
        idempotency_key=idempotency_key,
    )


def claim_daily_bonus(wallet, now=None):
    """Raises BonusNotReady if the last bonus was less than 24 hours ago."""
    now = now or timezone.now()
    with transaction.atomic():
        locked = Wallet.objects.select_for_update().get(pk=wallet.pk)
        if locked.last_bonus_at and now - locked.last_bonus_at < DAILY_BONUS_COOLDOWN:
            raise BonusNotReady(locked.last_bonus_at + DAILY_BONUS_COOLDOWN)
        tx = _apply(locked.id, Transaction.Kind.BONUS, DAILY_BONUS)
        Wallet.objects.filter(pk=locked.pk).update(last_bonus_at=now)
        return tx
