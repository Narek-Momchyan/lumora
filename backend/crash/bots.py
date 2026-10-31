"""Demo bots that fill the live feed. They are never in a wallet, the ledger or the leaderboard.

A bot's target is drawn before the flight and knows nothing about the crash point, so it wins
and loses like a player. SystemRandom, because the project never uses `random`'s generator;
nothing here decides a game result.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal
from random import SystemRandom

from django.db import transaction

from . import engine, feed
from .models import CrashBotBet, CrashBotSettings, CrashRound

rng = SystemRandom()
CENT = Decimal("0.01")
MIN_TARGET = Decimal("1.10")
MAX_TARGET = Decimal("20.00")


@dataclass
class PlannedBet:
    at: datetime
    name: str
    amount: Decimal
    target: Decimal


def _target():
    # Mostly small targets with a few big ones, like real players.
    drawn = Decimal(str(1 / (1 - rng.random()))).quantize(CENT)
    return min(MAX_TARGET, max(MIN_TARGET, drawn))


def _amount(config):
    return max(config.min_bet, Decimal(rng.randint(int(config.min_bet), int(config.max_bet)))).quantize(CENT)


def plan_round(betting_ends_at):
    """Who bets in the next betting window, how much, and when. Empty when the bots are off."""
    config = CrashBotSettings.load()
    if not config.is_enabled:
        return []
    names = config.name_list()
    window_ms = engine.BETTING_SECONDS * 1000
    bets = [
        PlannedBet(
            at=betting_ends_at - timedelta(milliseconds=rng.randint(300, window_ms - 200)),
            name=name,
            amount=_amount(config),
            target=_target(),
        )
        for name in rng.sample(names, min(config.count, len(names)))
    ]
    return sorted(bets, key=lambda bet: bet.at)


def place(round_id, planned):
    """Add a planned bet to the round, unless its betting window has already ended."""
    with transaction.atomic():
        current = CrashRound.objects.select_for_update().get(pk=round_id)
        if current.status != CrashRound.Status.BETTING:
            return None
        bot = CrashBotBet.objects.create(
            round=current, name=planned.name, amount=planned.amount, target=planned.target
        )
        data = feed.bot_bet_data(bot)
        transaction.on_commit(lambda: feed.publish("bet.placed", data), robust=True)
    return bot
