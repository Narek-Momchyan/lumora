"""Football bets: placing a single or an express, and settling it on the regular-time score.

Money moves only through wallet.services (Rule 2). Locks are always taken in the same order, so
two requests can never wait for each other:
    placing:  selection rows (by id) → wallet
    settling: bet row → wallet
    pricing:  selection rows only (sports/odds.py)
"""

from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_DOWN, Decimal

from django.db import transaction
from django.utils import timezone

from wallet.models import Wallet
from wallet.services import credit, debit, refund
from . import engine
from .models import Bet, BetSelection, Market, Match, Selection

GAME = "football"
MIN_STAKE = Decimal("1.00")
MAX_STAKE = Decimal("5000.00")
MAX_PICKS = 10
MAX_TOTAL_ODDS = Decimal("1000.00")
MAX_WIN = Decimal("100000.00")
SUSPENDED_VOID_AFTER = timedelta(hours=48)  # football-data has no "abandoned": a suspension this old is one
CENTS = Decimal("0.01")


class BetError(Exception):
    status_code = 400

    def __init__(self, code, text, extra=None, **params):
        super().__init__(text)
        self.code = code
        self.params = params
        self.extra = extra or {}


class OddsChanged(BetError):
    """The player saw other odds: they get the new ones and confirm again."""

    status_code = 409


@dataclass(frozen=True)
class Pick:
    selection: int
    odds: Decimal  # the odds the player saw


def money(value):
    return Decimal(value).quantize(CENTS, rounding=ROUND_DOWN)


def check_shape(stake, picks):
    if not 1 <= len(picks) <= MAX_PICKS:
        raise BetError("too_many_selections", "A bet has 1 to {max} selections.", max=MAX_PICKS)
    if len({pick.selection for pick in picks}) != len(picks):
        raise BetError("same_match_twice", "One match can be in an express only once.")
    if stake < MIN_STAKE:
        raise BetError("stake_too_low", "The smallest stake is {min} LC.", min=MIN_STAKE)
    if stake > MAX_STAKE:
        raise BetError("stake_too_high", "The largest stake is {max} LC.", max=MAX_STAKE)


def find_bet(user, key):
    return Bet.objects.prefetch_related("picks").filter(user=user, key=key).first()


def place_bet(user, key, stake, picks, now=None):
    """Place a bet: returns (bet, created). A repeated `key` returns the first bet and charges nothing.

    Raises BetError (or OddsChanged, 409) and wallet.services.InsufficientFunds.
    """
    stake = money(stake)
    existing = find_bet(user, key)
    if existing:
        return existing, False
    check_shape(stake, picks)

    with transaction.atomic():
        now = now or timezone.now()
        ids = sorted(pick.selection for pick in picks)
        rows = {
            row.id: row
            for row in Selection.objects.select_for_update()
            .select_related("market__match")
            .filter(id__in=ids)
            .order_by("id")
        }
        existing = find_bet(user, key)  # a parallel retry waited for the locks above
        if existing:
            return existing, False
        if len(rows) != len(ids):
            raise BetError("market_closed", "This market is not open.")

        matches = [rows[pick.selection].market.match_id for pick in picks]
        if len(set(matches)) != len(matches):
            raise BetError("same_match_twice", "One match can be in an express only once.")

        changed = []
        for pick in picks:
            row = rows[pick.selection]
            if row.market.status != Market.Status.OPEN or row.market.match.kickoff <= now:
                raise BetError("market_closed", "Bets on this match closed at kickoff.")
            if row.odds != Decimal(pick.odds):
                changed.append({"selection": row.id, "odds": str(row.odds)})
        if changed:
            raise OddsChanged("odds_changed", "The odds have changed.", extra={"selections": changed})

        total_odds = Decimal(1)
        for pick in picks:
            total_odds *= rows[pick.selection].odds
        total_odds = total_odds.quantize(CENTS, rounding=ROUND_DOWN)
        if total_odds > MAX_TOTAL_ODDS:
            raise BetError("odds_too_high", "Total odds can be at most {max}.", max=MAX_TOTAL_ODDS)
        potential_win = money(stake * total_odds)
        if potential_win > MAX_WIN:
            raise BetError("win_too_high", "A bet can win at most {max} LC.", max=MAX_WIN)

        bet = Bet.objects.create(
            user=user,
            key=key,
            kind=Bet.Kind.SINGLE if len(picks) == 1 else Bet.Kind.EXPRESS,
            stake=stake,
            total_odds=total_odds,
            potential_win=potential_win,
        )
        wallet = Wallet.objects.get(user=user)
        debit(wallet, stake, game=GAME, round_id=f"bet:{bet.id}", idempotency_key=f"{GAME}:{key}"[:64])
        BetSelection.objects.bulk_create(
            BetSelection(bet=bet, selection=row, match_id=row.market.match_id, odds=row.odds)
            for row in (rows[pick.selection] for pick in picks)
        )
    return bet, True


# ---------------------------------------------------------------- settlement


def is_void(match, now):
    if match.status in (Match.Status.POSTPONED, Match.Status.CANCELLED, Match.Status.AWARDED):
        return True
    return match.status == Match.Status.SUSPENDED and now - match.kickoff >= SUSPENDED_VOID_AFTER


def market_outcome(market, now):
    """(market status, {code: result}) once the match is decided, else None."""
    match = market.match
    if is_void(match, now):
        return Market.Status.VOID, lambda code: Selection.Result.VOID
    if match.status != Match.Status.FINISHED or match.home_regular is None or match.away_regular is None:
        return None  # not over yet, or the regular-time score isn't known yet

    def result(code):
        won = engine.selection_wins(market.kind, market.line, code, match.home_regular, match.away_regular)
        return Selection.Result.WON if won else Selection.Result.LOST

    return Market.Status.SETTLED, result


def settle_markets(now=None):
    """Mark every selection of finished or void matches won / lost / void. Returns the markets settled."""
    now = now or timezone.now()
    count = 0
    open_markets = Market.objects.filter(status__in=[Market.Status.OPEN, Market.Status.CLOSED]).select_related("match")
    for market in open_markets:
        outcome = market_outcome(market, now)
        if outcome is None:
            continue
        status, result = outcome
        with transaction.atomic():
            for selection in market.selections.select_for_update():
                selection.result = result(selection.code)
                selection.save(update_fields=["result"])
            Market.objects.filter(pk=market.pk).update(status=status)
        count += 1
    return count


def settle_bets(now=None):
    """Pay every open bet whose picks are all decided. Safe to run again: a settled bet is skipped."""
    now = now or timezone.now()
    settled = 0
    for bet_id in Bet.objects.filter(status=Bet.Status.OPEN).values_list("id", flat=True):
        if settle_bet(bet_id, now):
            settled += 1
    return settled


def settle_bet(bet_id, now):
    with transaction.atomic():
        bet = Bet.objects.select_for_update().get(pk=bet_id)
        if bet.status != Bet.Status.OPEN:
            return False  # another run settled it while we waited for the lock
        picks = list(bet.picks.select_related("selection"))
        results = [pick.selection.result for pick in picks]
        if Selection.Result.PENDING in results:
            return False

        for pick in picks:
            pick.result = pick.selection.result
        BetSelection.objects.bulk_update(picks, ["result"])

        # A lost pick loses the bet; a void pick counts as odds 1.00; all void gives the stake back.
        wallet = Wallet.objects.get(user_id=bet.user_id)
        if Selection.Result.LOST in results:
            bet.status, bet.payout = Bet.Status.LOST, Decimal("0.00")
        elif all(result == Selection.Result.VOID for result in results):
            bet.status, bet.payout = Bet.Status.VOID, bet.stake
            key = f"{GAME}:{bet.id}:refund"
            refund(wallet, bet.stake, game=GAME, round_id=f"bet:{bet.id}", idempotency_key=key)
        else:
            odds = Decimal(1)
            for pick in picks:
                if pick.result == Selection.Result.WON:
                    odds *= pick.odds
            bet.status, bet.payout = Bet.Status.WON, money(bet.stake * odds)
            key = f"{GAME}:{bet.id}:payout"
            credit(wallet, bet.payout, game=GAME, round_id=f"bet:{bet.id}", idempotency_key=key)
        bet.settled_at = now
        bet.save(update_fields=["status", "payout", "settled_at"])
    return True


def settle(now=None):
    """Markets first, then the bets that depend on them. Runs after every football sync."""
    return settle_markets(now), settle_bets(now)
