"""What the /ws/roulette clients see. Only this file decides what is public about a round.

`result` goes out when the spin starts and `seed` after the settlement. Only data, no texts: the
frontend has its labels. Money stays a two-decimal string, as in the REST API.
"""

from datetime import timedelta
from decimal import Decimal

from django.utils import timezone

from base import live, names
from . import engine
from .models import RouletteBotBet, RouletteRound

GROUP = "roulette"
HISTORY_LENGTH = 14


def publish(event, data):
    live.publish(GROUP, event, data)


def _time(value):
    return value.isoformat() if value else None


def round_data(current):
    data = {
        "number": current.number,
        "status": current.status,
        "seed_hash": current.seed_hash,
        "betting_ends_at": _time(current.betting_ends_at),
        "server_time": _time(timezone.now()),
    }
    if current.status != RouletteRound.Status.BETTING:
        data |= {
            "spin_started_at": _time(current.spin_started_at),
            "spin_ends_at": _time(current.spin_started_at + timedelta(seconds=engine.SPIN_SECONDS)),
            "result": current.result,
            "color": engine.color(current.result),
        }
    if current.status == RouletteRound.Status.SETTLED:
        data |= {
            "seed": current.seed,
            "settled_at": _time(current.settled_at),
            "winning": engine.winning_outside_bets(current.result),
        }
    return data


def _line_data(bet_type, value, amount):
    return {"bet_type": bet_type, "value": value, "amount": str(amount)}


def slip_seat(user_id):
    """A seat at the table. The hash, not the user id: the id would be public and sequential."""
    return f"player-{names.public_id(user_id)}"


def slip_data(slip):
    return {
        "id": f"slip-{slip.pk}",
        "round": slip.round.number,
        "seat": slip_seat(slip.user_id),
        "player": live.player_name(slip.user),
        "is_bot": False,
        "amount": str(slip.amount),
        "payout": str(slip.payout),
        "lines": [_line_data(line.bet_type, line.value, line.amount) for line in slip.lines.all()],
    }


def bot_bet_data(bot):
    return {
        "id": f"bot-{bot.pk}",
        "round": bot.round.number,
        "seat": f"bot-{bot.pk}",
        "player": bot.name,
        "is_bot": True,
        "amount": str(bot.amount),
        "payout": str(bot.payout),
        "lines": bot.lines,
    }


def table_bets(current):
    slips = current.slips.select_related("user", "round").prefetch_related("lines").order_by("id")
    bots = RouletteBotBet.objects.filter(round=current).select_related("round")
    return [slip_data(slip) for slip in slips] + [bot_bet_data(bot) for bot in bots]


def payouts(current):
    """Who bet and won how much in a round, one row per seat: a player can have several slips."""
    seats = {}
    for bet in table_bets(current):
        seat = seats.setdefault(
            bet["seat"],
            {
                "seat": bet["seat"],
                "player": bet["player"],
                "is_bot": bet["is_bot"],
                "amount": Decimal("0.00"),
                "payout": Decimal("0.00"),
            },
        )
        seat["amount"] += Decimal(bet["amount"])
        seat["payout"] += Decimal(bet["payout"])
    return [seat | {"amount": str(seat["amount"]), "payout": str(seat["payout"])} for seat in seats.values()]


def snapshot():
    """The whole state, sent once to every new client."""
    current = RouletteRound.objects.first()
    history = RouletteRound.objects.exclude(status=RouletteRound.Status.BETTING)[:HISTORY_LENGTH]
    return {
        "round": round_data(current) if current else None,
        "history": [
            {"number": row.number, "result": row.result, "color": engine.color(row.result)} for row in history
        ],
        "bets": table_bets(current) if current else [],
        "server_time": _time(timezone.now()),
    }
