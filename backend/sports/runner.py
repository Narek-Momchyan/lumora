"""Keeps the football data fresh: one full sync a day, today's matches every few minutes on match days.

Like the live games' runners, only one runs at a time (a PostgreSQL advisory lock). runserver
starts it when FOOTBALL_DATA_TOKEN is set; in production run_sports keeps it going. The first
full sync runs at once when the database has none.
"""

import time
from datetime import datetime, time as day_time, timedelta

from django.conf import settings
from django.utils import timezone

from base import live
from . import services
from .models import SyncRun

LOCK_KEY = 7_203_003  # differs from crash's and roulette's
FULL_SYNC_AFTER = day_time(3, 0)  # UTC: after the night's matches are final
TICK_SECONDS = 60


def acquire_lock():
    return live.acquire_lock(LOCK_KEY)


class Runner:
    def __init__(self, client=None, clock=timezone.now, sleep=time.sleep):
        self.client = client or services.default_client()
        self.clock = clock
        self.sleep = sleep
        self.last_full: datetime | None = self._last_run(SyncRun.Kind.FULL)
        self.last_today: datetime | None = None

    @staticmethod
    def _last_run(kind):
        run = SyncRun.objects.filter(kind=kind, ok=True).order_by("-started_at").first()
        return run.started_at if run else None

    def full_is_due(self, now):
        if self.last_full is None:
            return True  # never synced: fill the database now, don't wait for the night
        due_from = datetime.combine(now.date(), FULL_SYNC_AFTER, tzinfo=now.tzinfo)
        return now >= due_from and self.last_full < due_from

    def today_is_due(self, now):
        interval = timedelta(minutes=settings.SPORTS_SYNC_INTERVAL_MINUTES)
        if self.last_today is not None and now - self.last_today < interval:
            return False
        return services.has_matches_today(now.date())

    def step(self):
        """One tick: at most one sync. Returns the kind it ran, or None."""
        now = self.clock()
        if self.full_is_due(now):
            services.run_sync(self.client, SyncRun.Kind.FULL, today=now.date())
            services.after_sync(now)
            self.last_full = self.last_today = now
            return SyncRun.Kind.FULL
        if self.today_is_due(now):
            services.run_sync(self.client, SyncRun.Kind.TODAY, today=now.date())
            services.after_sync(now)
            self.last_today = now
            return SyncRun.Kind.TODAY
        return None

    def run(self):
        while True:
            self.step()
            self.sleep(TICK_SECONDS)
