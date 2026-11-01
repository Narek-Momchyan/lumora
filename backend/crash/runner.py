"""The loop that moves the rounds, run by `python manage.py run_crash`.

step() reads everything it needs from the database, so a restarted runner simply continues the
round it finds there: the flight's time kept running, and a crash point it missed ends the
round on the first step.
"""

import time
from datetime import timedelta

from django.utils import timezone

from base import live
from . import bots, engine, services
from .models import CrashRound

TICK_SECONDS = 0.1
LOCK_KEY = 7_203_001  # any number, it only has to be the same in every runner


def acquire_lock():
    return live.acquire_lock(LOCK_KEY)


class Runner:
    def __init__(self):
        self.planned_bots = []

    def step(self, now=None):
        now = now or timezone.now()
        current = CrashRound.objects.first()
        if current is None or self._pause_is_over(current, now):
            current = services.open_round(now)
            self.planned_bots = bots.plan_round(current.betting_ends_at)
        elif current.status == CrashRound.Status.BETTING:
            self._place_due_bots(current, now)
            if now >= current.betting_ends_at:
                services.start_flight(current.pk, now)
        elif current.status == CrashRound.Status.FLYING:
            if services.live_multiplier(current, now) >= current.crash_point:
                services.crash_round(current.pk, now)
            else:
                services.pay_auto_cash_outs(current.pk, now)

    def run(self):
        while True:
            self.step()
            time.sleep(TICK_SECONDS)

    def _pause_is_over(self, current, now):
        return (
            current.status == CrashRound.Status.CRASHED
            and now >= current.crashed_at + timedelta(seconds=engine.PAUSE_SECONDS)
        )

    def _place_due_bots(self, current, now):
        while self.planned_bots and self.planned_bots[0].at <= now:
            bots.place(current.pk, self.planned_bots.pop(0))
