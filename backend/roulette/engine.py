"""European roulette (single zero). Pure functions: no database, no Django, easy to test.

A bet is a set of covered pockets. It pays 36 / (covered pockets) times the stake, so every bet
type has the same exact RTP: covered / 37 * 36 / covered = 36/37 = 97.30%.

resolve_bet() is the one place that knows which bets exist. The spin result comes from
fairness.rng: pocket = floor(r * 37).
"""

from decimal import Decimal

BETTING_SECONDS = 18
SPIN_SECONDS = 8
PAUSE_SECONDS = 4

MIN_LINE = Decimal("1.00")
MAX_LINES = 50  # one player, one round
MAX_ROUND_TOTAL = Decimal("10000.00")  # one player, one round

POCKETS = 37
RED = {1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36}
# The pockets clockwise, for the frontend to stop the wheel on the right one.
WHEEL = [
    0, 32, 15, 19, 4, 21, 2, 25, 17, 34, 6, 27, 13, 36, 11, 30, 8, 23, 10, 5, 24, 16, 33, 1, 20, 14, 31, 9, 22, 18,
    29, 7, 28, 12, 35, 3, 26,
]  # fmt: skip

NUMBERS = range(1, 37)

# The felt has 12 rows of 3: 1 2 3 / 4 5 6 / ... / 34 35 36, with 0 next to 1, 2 and 3.
OUTSIDE = {
    "red": frozenset(RED),
    "black": frozenset(NUMBERS) - RED,
    "even": frozenset(n for n in NUMBERS if n % 2 == 0),
    "odd": frozenset(n for n in NUMBERS if n % 2 == 1),
    "low": frozenset(range(1, 19)),
    "high": frozenset(range(19, 37)),
}
DOZENS = {d: frozenset(range(12 * d - 11, 12 * d + 1)) for d in (1, 2, 3)}
COLUMNS = {c: frozenset(n for n in NUMBERS if (n - 1) % 3 == c - 1) for c in (1, 2, 3)}

ALL_BETS = {
    "straight": [[n] for n in range(POCKETS)],
    "split": (
        [[0, n] for n in (1, 2, 3)]
        + [[n, n + 1] for n in NUMBERS if n % 3 != 0]
        + [[n, n + 3] for n in range(1, 34)]
    ),
    "street": [[n, n + 1, n + 2] for n in range(1, 35, 3)],
    "trio": [[0, 1, 2], [0, 2, 3]],
    "corner": [[n, n + 1, n + 3, n + 4] for n in range(1, 33) if n % 3 != 0],
    "first_four": [[0, 1, 2, 3]],
    "six_line": [[n, n + 1, n + 2, n + 3, n + 4, n + 5] for n in range(1, 32, 3)],
    "dozen": [[d] for d in DOZENS],
    "column": [[c] for c in COLUMNS],
    **{name: [[]] for name in OUTSIDE},
}


class InvalidBet(ValueError):
    pass


def resolve_bet(bet_type, value):
    """Check a bet and return (covered pockets, multiplier including the stake).

    `value` is a list: the numbers of an inside bet ([8, 11]), the number of a dozen or column
    ([2]), empty for red, black and the like. Raises InvalidBet for a bet the table doesn't have,
    for example the split 8/12.
    """
    value = list(value)
    if any(type(number) is not int for number in value):
        raise InvalidBet(f"Not numbers: {value}")
    value = sorted(value)
    if bet_type not in ALL_BETS or value not in ALL_BETS[bet_type]:
        raise InvalidBet(f"No such bet: {bet_type} {value}")
    if bet_type in OUTSIDE:
        covered = OUTSIDE[bet_type]
    elif bet_type == "dozen":
        covered = DOZENS[value[0]]
    elif bet_type == "column":
        covered = COLUMNS[value[0]]
    else:
        covered = frozenset(value)
    return covered, 36 // len(covered)


def pocket(r):
    return int(r * POCKETS)


def color(result):
    if result == 0:
        return "green"
    return "red" if result in RED else "black"


def payout(bet_type, value, amount, result):
    covered, multiplier = resolve_bet(bet_type, value)
    return amount * multiplier if result in covered else Decimal("0.00")


def winning_outside_bets(result):
    """The outside bets a result wins, for the frontend to light up: [{"bet_type": "dozen", "value": [2]}, ...]"""
    return [
        {"bet_type": bet_type, "value": value}
        for bet_type in [*OUTSIDE, "dozen", "column"]
        for value in ALL_BETS[bet_type]
        if result in resolve_bet(bet_type, value)[0]
    ]
