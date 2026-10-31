"""Neon Crash maths. Pure functions: no database, no Django, easy to test.

Crash point from a uniform float r in [0, 1):
    point = floor(100 * (1 - HOUSE_EDGE) / (1 - r)) / 100, at least 1.00, at most MAX_TARGET

For any cash-out target m >= 1:
    P(point >= m) = (1 - HOUSE_EDGE) / m        (before flooring)
    expected return = P * m = 1 - HOUSE_EDGE = 97%
So every target has the same RTP. Flooring to 2 decimals shaves off a tiny bit more;
the simulation test in tests.py measures the real number. The MAX_TARGET cap changes nothing
for a player, because no target can be higher.

The multiplier is a function of the time since the flight started:
    multiplier = floor(100 * e^(GROWTH_PER_MS * ms)) / 100
The frontend draws with the same formula, and the server recomputes it on every cash-out.
"""

from decimal import ROUND_DOWN, ROUND_FLOOR, Decimal

HOUSE_EDGE = Decimal("0.03")
MIN_TARGET = Decimal("1.01")
MAX_TARGET = Decimal("1000000")
GROWTH_PER_MS = Decimal("0.00006")  # 2x after about 11.6 s, 10x after about 38 s

BETTING_SECONDS = 7
PAUSE_SECONDS = 3


def crash_point(r):
    if not 0 <= r < 1:
        raise ValueError("r must be in [0, 1)")
    # Exact Decimal maths: no float rounding surprises at the 2-decimal boundary.
    hundredths = (100 * (1 - HOUSE_EDGE) / (1 - Decimal(r))).to_integral_value(rounding=ROUND_FLOOR)
    return min(MAX_TARGET, max(Decimal("1.00"), (hundredths / 100).quantize(Decimal("0.01"))))


def multiplier_at(elapsed_ms):
    """The multiplier elapsed_ms after the flight started, floored to 2 decimals."""
    if elapsed_ms <= 0:
        return Decimal("1.00")
    multiplier = (GROWTH_PER_MS * Decimal(elapsed_ms)).exp()
    if multiplier >= MAX_TARGET:
        return MAX_TARGET
    return multiplier.quantize(Decimal("0.01"), rounding=ROUND_FLOOR)


def payout(amount, target, point):
    """A win pays amount * target if the round reached the target, otherwise 0."""
    if point >= target:
        return (amount * target).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return Decimal("0.00")
