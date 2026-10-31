"""What the /ws/crash clients see. Only this file decides what is public about a round.

`seed` and `crash_point` go out only after the crash. Everything is plain strings and numbers,
because the channel layer carries it as msgpack: money and multipliers stay two-decimal strings,
as in the REST API.
"""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.utils import timezone

from .models import CrashBotBet, CrashRound

GROUP = "crash"
HISTORY_LENGTH = 20

logger = logging.getLogger(__name__)


def publish(event, data):
    """Send an event to every client. If Redis is down the game goes on without a live feed."""
    try:
        async_to_sync(get_channel_layer().group_send)(GROUP, {"type": "crash.event", "event": event, "data": data})
    except Exception:
        logger.exception("Could not publish %s", event)


def _time(value):
    return value.isoformat() if value else None


def round_data(current):
    data = {
        "number": current.number,
        "status": current.status,
        "seed_hash": current.seed_hash,
        "betting_ends_at": _time(current.betting_ends_at),
        "started_at": _time(current.started_at),
        "server_time": _time(timezone.now()),
    }
    if current.status == CrashRound.Status.CRASHED:
        data |= {
            "crash_point": str(current.crash_point),
            "seed": current.seed,
            "crashed_at": _time(current.crashed_at),
        }
    return data


def player_name(user):
    return user.display_name or user.email.split("@")[0]


def bet_data(bet):
    return {
        "id": f"player-{bet.pk}",
        "round": bet.round.number,
        "player": player_name(bet.user),
        "amount": str(bet.amount),
        "multiplier": None if bet.multiplier is None else str(bet.multiplier),
        "payout": str(bet.payout),
        "is_bot": False,
    }


def bot_bet_data(bot):
    return {
        "id": f"bot-{bot.pk}",
        "round": bot.round.number,
        "player": bot.name,
        "amount": str(bot.amount),
        "multiplier": None if bot.multiplier is None else str(bot.multiplier),
        "payout": str(bot.payout),
        "is_bot": True,
    }


def snapshot():
    """The whole state, sent once to every new client."""
    current = CrashRound.objects.first()
    history = CrashRound.objects.filter(status=CrashRound.Status.CRASHED)[:HISTORY_LENGTH]
    bets = []
    if current is not None:
        bets = [bet_data(bet) for bet in current.bets.select_related("user", "round").order_by("id")]
        bets += [bot_bet_data(bot) for bot in CrashBotBet.objects.filter(round=current).select_related("round")]
    return {
        "round": round_data(current) if current else None,
        "history": [{"number": row.number, "crash_point": str(row.crash_point)} for row in history],
        "bets": bets,
        "server_time": _time(timezone.now()),
    }
