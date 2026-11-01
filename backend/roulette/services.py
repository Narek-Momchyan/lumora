"""Live Lumora Roulette: one shared table, the same spin for every player.

The round moves betting -> spinning -> settled. roulette/runner.py is the only code that moves it,
the REST views only place bets.

Every function that touches a live round first locks its row, always in the order round, wallet.
So a bet and the end of the betting window can never run at the same time.
"""

from datetime import timedelta
from decimal import Decimal, InvalidOperation
from functools import partial

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from fairness.chain import next_link, seed_at
from fairness.rng import first_float, hash_seed
from games.models import Game
from wallet import services as wallet_services
from wallet.models import Wallet
from . import engine, feed
from .models import RouletteBotBet, RouletteChain, RouletteLine, RouletteRound, RouletteSlip

GAME_SLUG = "lumora-roulette"
CHAIN_LENGTH = 100_000
CENT = Decimal("0.01")


class RouletteError(Exception):
    status_code = 400

    def __init__(self, code, text, **params):
        super().__init__(text)
        self.code = code
        self.params = params


class RoundConflict(RouletteError):
    """The request was fine, but not at this moment of the round."""

    status_code = 409


def round_result(seed):
    """The winning pocket of a round. Anyone can recompute it from the revealed seed."""
    return engine.pocket(first_float(seed, GAME_SLUG, 0))


def open_round(now=None):
    """Start the next round of the chain and its betting window."""
    now = now or timezone.now()
    with transaction.atomic():
        last = RouletteRound.objects.first()
        chain, position = next_link(RouletteChain, last, CHAIN_LENGTH)
        seed = seed_at(chain, position)
        current = RouletteRound.objects.create(
            number=last.number + 1 if last else 1,
            chain=chain,
            position=position,
            seed=seed,
            seed_hash=hash_seed(seed),
            result=round_result(seed),
            betting_ends_at=now + timedelta(seconds=engine.BETTING_SECONDS),
        )
        RouletteBotBet.objects.exclude(round=current).delete()
        _publish_on_commit("round.betting", feed.round_data(current))
    return current


def start_spin(round_id, now=None):
    """No more bets. The result goes out now, so that the wheel can stop on it."""
    with transaction.atomic():
        current = RouletteRound.objects.select_for_update().get(pk=round_id)
        if current.status != RouletteRound.Status.BETTING:
            return current
        current.status = RouletteRound.Status.SPINNING
        current.spin_started_at = now or timezone.now()
        current.save(update_fields=["status", "spin_started_at"])
        _publish_on_commit("round.spinning", feed.round_data(current))
    return current


def settle_round(round_id, now=None):
    """Pay every winning slip with one credit and reveal the seed. A second call does nothing."""
    with transaction.atomic():
        current = RouletteRound.objects.select_for_update().get(pk=round_id)
        if current.status != RouletteRound.Status.SPINNING:
            return current
        for slip in current.slips.prefetch_related("lines"):
            _settle_slip(slip, current)
        for bot in current.bot_bets.all():
            bot.payout = sum(
                (
                    engine.payout(line["bet_type"], line["value"], Decimal(line["amount"]), current.result)
                    for line in bot.lines
                ),
                Decimal("0.00"),
            )
            bot.save(update_fields=["payout"])
        current.status = RouletteRound.Status.SETTLED
        current.settled_at = now or timezone.now()
        current.save(update_fields=["status", "settled_at"])
        _publish_on_commit("round.settled", {**feed.round_data(current), "payouts": feed.payouts(current)})
    return current


def place_bet(user, key, lines):
    """Put a slip on the open round and return (slip, created).

    A repeated `key` returns the first slip and charges nothing, whatever the round is by then.
    Raises RouletteError for a bad slip and wallet.services.InsufficientFunds for a low balance.
    """
    existing = _find_slip(user, key)
    if existing:
        return existing, False

    lines = [_clean_line(line) for line in lines]
    if not lines:
        raise RouletteError("invalid_bet", "This bet doesn't exist on the table.")
    amount = sum((line["amount"] for line in lines), Decimal("0.00"))
    if not Game.objects.filter(slug=GAME_SLUG, is_active=True).exists():
        raise RouletteError("game_unavailable", "This game is not available right now.")

    wallet = wallet_services.open_wallet(user)
    with transaction.atomic():
        current = RouletteRound.objects.select_for_update().first()
        existing = _find_slip(user, key)  # a parallel retry waited for the lock above
        if existing:
            return existing, False
        if (
            current is None
            or current.status != RouletteRound.Status.BETTING
            or timezone.now() >= current.betting_ends_at
        ):
            raise RoundConflict("round_closed", "Betting for this round is closed.")

        slips = current.slips.filter(user=user)
        if RouletteLine.objects.filter(slip__in=slips).count() + len(lines) > engine.MAX_LINES:
            raise RouletteError(
                "too_many_lines", f"At most {engine.MAX_LINES} bets in a round.", max=engine.MAX_LINES
            )
        if (slips.aggregate(total=Sum("amount"))["total"] or 0) + amount > engine.MAX_ROUND_TOTAL:
            raise RouletteError(
                "round_limit_exceeded",
                f"At most {engine.MAX_ROUND_TOTAL} LC in a round.",
                max=engine.MAX_ROUND_TOTAL,
            )

        wallet_services.debit(
            wallet,
            amount,
            game=GAME_SLUG,
            round_id=f"roulette:{current.number}",
            idempotency_key=f"roulette:{current.number}:{key}",
        )
        slip = RouletteSlip.objects.create(round=current, user=user, key=key, amount=amount)
        RouletteLine.objects.bulk_create(RouletteLine(slip=slip, **line) for line in lines)
        _publish_on_commit("bet.placed", feed.slip_data(slip))
    return slip, True


def last_round_lines(user):
    """The player's lines of their last settled round, for Rebet."""
    slip = (
        RouletteSlip.objects.filter(user=user, round__status=RouletteRound.Status.SETTLED)
        .select_related("round")
        .order_by("-round__number")
        .first()
    )
    if slip is None:
        return None, []
    return slip.round, RouletteLine.objects.filter(slip__round=slip.round, slip__user=user)


def _find_slip(user, key):
    return RouletteSlip.objects.select_related("round").filter(user=user, key=key).first()


def _clean_line(line):
    try:
        amount = Decimal(str(line["amount"]))
        _, multiplier = engine.resolve_bet(line["bet_type"], line.get("value", []))
        if amount != amount.quantize(CENT):
            raise ValueError("More than two decimals")
    except (KeyError, TypeError, ValueError, InvalidOperation) as exc:
        raise RouletteError("invalid_bet", "This bet doesn't exist on the table.") from exc
    if not engine.MIN_LINE <= amount <= engine.MAX_ROUND_TOTAL:
        raise RouletteError(
            "bet_out_of_range",
            f"Bet must be between {engine.MIN_LINE} and {engine.MAX_ROUND_TOTAL} LC.",
            min=engine.MIN_LINE,
            max=engine.MAX_ROUND_TOTAL,
        )
    return {
        "bet_type": line["bet_type"],
        "value": sorted(line.get("value", [])),
        "multiplier": multiplier,
        "amount": amount.quantize(CENT),
    }


def _settle_slip(slip, current):
    lines = list(slip.lines.all())
    for line in lines:
        line.payout = engine.payout(line.bet_type, line.value, line.amount, current.result)
    RouletteLine.objects.bulk_update(lines, ["payout"])
    slip.payout = sum((line.payout for line in lines), Decimal("0.00"))
    if slip.payout > 0:
        wallet_services.credit(
            Wallet.objects.get(user_id=slip.user_id),
            slip.payout,
            game=GAME_SLUG,
            round_id=f"roulette:{current.number}",
            idempotency_key=f"roulette:{slip.pk}:win",
        )
    slip.save(update_fields=["payout"])


def _publish_on_commit(event, data):
    # robust: the money is already safe by then, a broken feed must not raise into the caller.
    transaction.on_commit(partial(feed.publish, event, data), robust=True)
