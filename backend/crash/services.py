"""Settle a Neon Crash round: bet, roll, pay, all in one database transaction.

Phase 1 is "solo crash": the player picks an auto cash-out target and the round is settled
at once from their provably fair seeds. Live multiplayer rounds over WebSockets come later
(phase 2 in CLAUDE.md) and will reuse engine.py.
"""

from decimal import Decimal, InvalidOperation

from django.db import transaction

from fairness.rng import first_float
from fairness.services import next_nonce
from games.models import Game
from wallet import services as wallet_services
from . import engine
from .models import CrashBet

GAME_SLUG = "neon-crash"


class CrashError(Exception):
    pass


def _decimal(value, field):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise CrashError(f"Invalid {field}") from exc


def play(user, amount, target):
    """Raises CrashError for a bad bet and wallet.services.InsufficientFunds for a low balance."""
    amount = _decimal(amount, "amount")
    target = _decimal(target, "target")
    game = Game.objects.filter(slug=GAME_SLUG, is_active=True).first()
    if game is None:
        raise CrashError("Neon Crash is not available right now.")
    if not game.min_bet <= amount <= game.max_bet:
        raise CrashError(f"Bet must be between {game.min_bet} and {game.max_bet} LC.")
    if not engine.MIN_TARGET <= target <= engine.MAX_TARGET:
        raise CrashError(f"Target must be between {engine.MIN_TARGET}x and {engine.MAX_TARGET}x.")

    wallet = wallet_services.open_wallet(user)
    with transaction.atomic():
        pair, nonce = next_nonce(user)
        round_id = f"crash:{pair.pk}:{nonce}"
        wallet_services.debit(wallet, amount, game=GAME_SLUG, round_id=round_id)
        point = engine.crash_point(first_float(pair.server_seed, pair.client_seed, nonce))
        win = engine.payout(amount, target, point)
        if win > 0:
            wallet_services.credit(wallet, win, game=GAME_SLUG, round_id=round_id)
        return CrashBet.objects.create(
            user=user,
            amount=amount,
            target=target,
            crash_point=point,
            payout=win,
            server_seed_hash=pair.server_seed_hash,
            client_seed=pair.client_seed,
            nonce=nonce,
        )
