"""Demo bots that fill the live table. They are never in a wallet, the ledger or the leaderboard.

A bot's bets are chosen without knowing the result. SystemRandom, because the project never uses
`random`'s generator; nothing here decides a game result.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from random import SystemRandom

from django.db import transaction

from . import engine, feed
from .models import RouletteBotBet, RouletteBotSettings, RouletteRound

rng = SystemRandom()
CENT = Decimal("0.01")
MAX_BOT_LINES = 3
FIRST_BET_MS = 500


@dataclass
class PlannedBet:
    at: datetime
    name: str
    amount: Decimal
    lines: list


def _amount(config):
    return max(config.min_bet, Decimal(rng.randint(int(config.min_bet), int(config.max_bet)))).quantize(CENT)


def _lines(amount):
    count = min(rng.randint(1, MAX_BOT_LINES), int(amount))
    share = (amount / count).quantize(CENT)
    shares = [share] * (count - 1) + [amount - share * (count - 1)]
    lines = []
    for bet_type in rng.sample(list(engine.ALL_BETS), count):
        value = rng.choice(engine.ALL_BETS[bet_type])
        lines.append({"bet_type": bet_type, "value": value, "amount": str(shares[len(lines)])})
    return lines


def plan_round(betting_ends_at):
    """Who bets in the next betting window, what, and when. Empty when the bots are off."""
    config = RouletteBotSettings.load()
    if not config.is_enabled:
        return []
    names = config.name_list()
    window_ms = engine.BETTING_SECONDS * 1000
    bets = []
    for name in rng.sample(names, min(config.count, len(names))):
        amount = _amount(config)
        at = betting_ends_at - timedelta(milliseconds=rng.randint(FIRST_BET_MS, window_ms - FIRST_BET_MS))
        bets.append(PlannedBet(at=at, name=name, amount=amount, lines=_lines(amount)))
    return sorted(bets, key=lambda bet: bet.at)


def place(round_id, planned):
    """Add a planned bet to the round, unless its betting window has already ended."""
    with transaction.atomic():
        current = RouletteRound.objects.select_for_update().get(pk=round_id)
        if current.status != RouletteRound.Status.BETTING:
            return None
        bot = RouletteBotBet.objects.create(
            round=current, name=planned.name, lines=planned.lines, amount=planned.amount
        )
        data = feed.bot_bet_data(bot)
        transaction.on_commit(lambda: feed.publish("bet.placed", data), robust=True)
    return bot
