"""European roulette (single zero) payout rules. Pure functions.

RTP for every bet type is 36/37 = 97.30%. The spin result comes from fairness.rng:
pocket = floor(r * 37). The API + wallet wiring (phase 3) follows crash/services.py.
"""

from decimal import Decimal

RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}

# bet type -> (payout multiplier including the stake, wins(pocket, value))
BETS = {
    "straight": (36, lambda p, v: p == int(v)),
    "red": (2, lambda p, v: p in RED),
    "black": (2, lambda p, v: p != 0 and p not in RED),
    "even": (2, lambda p, v: p != 0 and p % 2 == 0),
    "odd": (2, lambda p, v: p % 2 == 1),
    "low": (2, lambda p, v: 1 <= p <= 18),
    "high": (2, lambda p, v: 19 <= p <= 36),
    "dozen": (3, lambda p, v: p != 0 and (p - 1) // 12 == int(v) - 1),
    "column": (3, lambda p, v: p != 0 and (p - 1) % 3 == int(v) - 1),
}


def pocket(r):
    return int(r * 37)


def payout(bet_type, value, amount, result):
    multiplier, wins = BETS[bet_type]
    return amount * multiplier if wins(result, value) else Decimal("0.00")
