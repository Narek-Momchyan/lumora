"""Live Neon Crash: one shared round at a time, the same for every player.

The round moves betting -> flying -> crashed. crash/runner.py is the only code that moves it,
the REST views only place bets and cash out.

Every function that touches a live round first locks its row, always in the order round, bet,
wallet. So a cash-out and the crash can never run at the same time: whichever gets the lock
second sees what the first one did.

Times are read after the lock, because waiting for it takes time too.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import partial

from django.db import transaction
from django.utils import timezone

from fairness.chain import next_link, seed_at
from fairness.rng import first_float, hash_seed
from games.models import Game
from wallet import services as wallet_services
from wallet.models import Wallet
from . import engine, feed
from .models import CrashBotBet, CrashChain, CrashRound, RoundBet

GAME_SLUG = "neon-crash"
CHAIN_LENGTH = 100_000


class CrashError(Exception):
    status_code = 400

    def __init__(self, code, text, **params):
        super().__init__(text)
        self.code = code
        self.params = params


class RoundConflict(CrashError):
    """The request was fine, but not at this moment of the round."""

    status_code = 409


def _decimal(value, field):
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as exc:
        raise CrashError("invalid", f"Invalid {field}") from exc


def round_result(seed):
    """The crash point of a round. Anyone can recompute it from the revealed seed."""
    return engine.crash_point(first_float(seed, GAME_SLUG, 0))


def live_multiplier(current, now):
    return engine.multiplier_at((now - current.started_at) // timedelta(milliseconds=1))


def open_round(now=None):
    """Start the next round of the chain and its betting window."""
    now = now or timezone.now()
    with transaction.atomic():
        last = CrashRound.objects.first()
        chain, position = next_link(CrashChain, last, CHAIN_LENGTH)
        seed = seed_at(chain, position)
        current = CrashRound.objects.create(
            number=last.number + 1 if last else 1,
            chain=chain,
            position=position,
            seed=seed,
            seed_hash=hash_seed(seed),
            crash_point=round_result(seed),
            betting_ends_at=now + timedelta(seconds=engine.BETTING_SECONDS),
        )
        CrashBotBet.objects.exclude(round=current).delete()
        _publish_on_commit("round.betting", feed.round_data(current))
    return current


def start_flight(round_id, now=None):
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().get(pk=round_id)
        if current.status != CrashRound.Status.BETTING:
            return current
        current.status = CrashRound.Status.FLYING
        current.started_at = now or timezone.now()
        current.save(update_fields=["status", "started_at"])
        _publish_on_commit("round.flying", feed.round_data(current))
    return current


def pay_auto_cash_outs(round_id, now=None):
    """Pay every bet whose auto cash-out target the flight has passed. The runner calls this on every tick."""
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().get(pk=round_id)
        if current.status == CrashRound.Status.FLYING:
            _pay_targets_up_to(current, min(live_multiplier(current, now or timezone.now()), current.crash_point))


def crash_round(round_id, now=None):
    """End the flight: pay the targets it reached, lose the rest and reveal the seed."""
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().get(pk=round_id)
        if current.status != CrashRound.Status.FLYING:
            return current
        _pay_targets_up_to(current, current.crash_point)
        current.bets.filter(status=RoundBet.Status.ACTIVE).update(status=RoundBet.Status.LOST)
        current.status = CrashRound.Status.CRASHED
        current.crashed_at = now or timezone.now()
        current.save(update_fields=["status", "crashed_at"])
        _publish_on_commit("round.crashed", feed.round_data(current))
    return current


def place_bet(user, amount, target=None):
    """Raises CrashError for a bad bet and wallet.services.InsufficientFunds for a low balance."""
    amount = _decimal(amount, "amount")
    target = None if target is None else _decimal(target, "target")
    game = Game.objects.filter(slug=GAME_SLUG, is_active=True).first()
    if game is None:
        raise CrashError("game_unavailable", "This game is not available right now.")
    if not game.min_bet <= amount <= game.max_bet:
        raise CrashError(
            "bet_out_of_range",
            f"Bet must be between {game.min_bet} and {game.max_bet} LC.",
            min=game.min_bet,
            max=game.max_bet,
        )
    if target is not None and not engine.MIN_TARGET <= target <= engine.MAX_TARGET:
        raise CrashError(
            "target_out_of_range",
            f"Target must be between {engine.MIN_TARGET}x and {engine.MAX_TARGET}x.",
            min=engine.MIN_TARGET,
            max=engine.MAX_TARGET,
        )

    wallet = wallet_services.open_wallet(user)
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().first()
        if (
            current is None
            or current.status != CrashRound.Status.BETTING
            or timezone.now() >= current.betting_ends_at
        ):
            raise RoundConflict("round_closed", "Betting for this round is closed.")
        if current.bets.filter(user=user).exists():
            raise RoundConflict("already_bet", "You already have a bet on this round.")
        wallet_services.debit(
            wallet,
            amount,
            game=GAME_SLUG,
            round_id=f"crash:{current.number}",
            idempotency_key=f"crash:{current.number}:bet",
        )
        bet = RoundBet.objects.create(round=current, user=user, amount=amount, target=target)
        _publish_on_commit("bet.placed", feed.bet_data(bet))
    return bet


def cash_out(user, now=None):
    """Pay the player's bet at the multiplier of this moment, by the server's own clock.

    Raises RoundConflict. `too_late` also covers a crash point the clock has passed while the
    runner has not ended the round yet, so the crash event doesn't have to arrive first.
    """
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().first()
        bet = None
        if current is not None:
            bet = RoundBet.objects.select_for_update().filter(round=current, user=user).first()
        if bet is None:
            raise RoundConflict("no_bet", "You have no bet on this round.")
        if bet.status == RoundBet.Status.CASHED_OUT:
            raise RoundConflict("already_cashed_out", "This bet is already cashed out.")
        if bet.status == RoundBet.Status.LOST:
            raise RoundConflict("too_late", "Too late, the round has crashed.")
        if current.status != CrashRound.Status.FLYING:
            raise RoundConflict("not_flying", "The round has not started yet.")

        multiplier = live_multiplier(current, now or timezone.now())
        if bet.target is not None and bet.target <= min(multiplier, current.crash_point):
            # The auto cash-out was reached first, the runner just hasn't paid it yet.
            multiplier = bet.target
        elif multiplier >= current.crash_point:
            raise RoundConflict("too_late", "Too late, the round has crashed.")
        _pay_bet(bet, multiplier, current)
    return bet


def _pay_targets_up_to(current, multiplier):
    for bet in current.bets.select_for_update().filter(status=RoundBet.Status.ACTIVE, target__lte=multiplier):
        _pay_bet(bet, bet.target, current)
    for bot in current.bot_bets.filter(multiplier__isnull=True, target__lte=multiplier):
        bot.multiplier = bot.target
        bot.payout = engine.payout(bot.amount, bot.target, current.crash_point)
        bot.save(update_fields=["multiplier", "payout"])
        _publish_on_commit("bet.cashed_out", feed.bot_bet_data(bot))


def _pay_bet(bet, multiplier, current):
    payout = engine.payout(bet.amount, multiplier, current.crash_point)
    wallet_services.credit(
        Wallet.objects.get(user_id=bet.user_id),
        payout,
        game=GAME_SLUG,
        round_id=f"crash:{current.number}",
        idempotency_key=f"crash:{current.number}:win",
    )
    bet.status = RoundBet.Status.CASHED_OUT
    bet.multiplier = multiplier
    bet.payout = payout
    bet.save(update_fields=["status", "multiplier", "payout"])
    _publish_on_commit("bet.cashed_out", feed.bet_data(bet))


def _publish_on_commit(event, data):
    # robust: the money is already safe by then, a broken feed must not raise into the caller.
    transaction.on_commit(partial(feed.publish, event, data), robust=True)
