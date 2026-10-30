from decimal import Decimal

from django.test import SimpleTestCase

from . import engine


class RouletteEngineTests(SimpleTestCase):
    def test_every_bet_has_rtp_36_of_37(self):
        """Exact RTP: the average payout over all 37 pockets."""
        bets = [("straight", 17), ("red", None), ("black", None), ("even", None), ("odd", None),
                ("low", None), ("high", None), ("dozen", 2), ("column", 3)]
        for bet_type, value in bets:
            with self.subTest(bet=bet_type):
                total = sum(engine.payout(bet_type, value, Decimal("1"), p) for p in range(37))
                self.assertEqual(total / 37, Decimal(36) / Decimal(37))

    def test_zero_loses_every_outside_bet(self):
        for bet_type in ["red", "black", "even", "odd", "low", "high"]:
            with self.subTest(bet=bet_type):
                self.assertEqual(engine.payout(bet_type, None, Decimal("10"), 0), 0)

    def test_pocket_range(self):
        self.assertEqual(engine.pocket(0.0), 0)
        self.assertEqual(engine.pocket(0.999999), 36)
