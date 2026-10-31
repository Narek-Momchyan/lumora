"""Neon Crash maths. Pure functions: no database, no Django, easy to test.

Crash point from a uniform float r in [0, 1):
    point = floor(100 * (1 - HOUSE_EDGE) / (1 - r)) / 100, at least 1.00

For any cash-out target m >= 1:
    P(point >= m) = (1 - HOUSE_EDGE) / m        (before flooring)
    expected return = P * m = 1 - HOUSE_EDGE = 97%
So every target has the same RTP. Flooring to 2 decimals shaves off a tiny bit more;
the simulation test in tests.py measures the real number.
"""

from decimal import ROUND_DOWN, ROUND_FLOOR, Decimal

HOUSE_EDGE = Decimal("0.03")
MIN_TARGET = Decimal("1.01")
MAX_TARGET = Decimal("1000000")


def crash_point(r):
    if not 0 <= r < 1:
        raise ValueError("r must be in [0, 1)")
    # Exact Decimal maths: no float rounding surprises at the 2-decimal boundary.
    hundredths = (100 * (1 - HOUSE_EDGE) / (1 - Decimal(r))).to_integral_value(rounding=ROUND_FLOOR)
    return max(Decimal("1.00"), (hundredths / 100).quantize(Decimal("0.01")))


def payout(amount, target, point):
    """A win pays amount * target if the round reached the target, otherwise 0."""
    if point >= target:
        return (amount * target).quantize(Decimal("0.01"), rounding=ROUND_DOWN)
    return Decimal("0.00")
