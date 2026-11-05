"""Keeps the live scores fresh. Display only: nothing here settles a bet or a prediction, changes
odds, or writes a Match's own score (design/sports-spec.md section 2; Rules 14 and 15).

Like run_sports, one runner at a time (a PostgreSQL advisory lock) and `runserver` does not start it:
every poll spends API-Football's free quota (100 requests a day). Each step:

1. The matches inside [kickoff, kickoff + LIVE_WINDOW_MINUTES] are the ones worth showing. With none,
   nothing is asked and nothing is spent.
2. With API-Football on and budget left (LIVE_DAILY_LIMIT, counted in the database), ONE request
   `fixtures?live=all` is made; its fixtures are matched to our matches (sports/live_matching.py).
3. A match the API gave us shows the API's score and minute. One it did not, that football-data.org
   says is live, shows football-data's delayed score, marked as delayed. A match that left the window
   or that football-data says is over disappears from the live page.
"""

import logging
import time
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from base import live
from . import feed, live_matching
from .models import ApiUsage, LiveScore, Match
from .providers.api_football import ApiFootballClient
from .providers.football_data import ProviderError

LOCK_KEY = 7_203_004  # differs from crash's, roulette's and run_sports'
logger = logging.getLogger(__name__)

PLAYING = {"1H", "2H", "ET", "BT", "P", "LIVE", "INT", "SUSP"}
ENDED = {"FT", "AET", "PEN"}
SKIPPED = (Match.Status.POSTPONED, Match.Status.CANCELLED, Match.Status.AWARDED)


def acquire_lock():
    return live.acquire_lock(LOCK_KEY)


def default_client():
    """The API-Football client, or None when it is off or has no key (football-data's score is shown)."""
    if not settings.API_FOOTBALL_ENABLED or not settings.API_FOOTBALL_KEY:
        return None
    return ApiFootballClient(settings.API_FOOTBALL_KEY)


def window_matches(now):
    """Matches that kicked off at most LIVE_WINDOW_MINUTES ago and are not off."""
    since = now - timedelta(minutes=settings.LIVE_WINDOW_MINUTES)
    return list(
        Match.objects.filter(competition__is_active=True, kickoff__lte=now, kickoff__gte=since)
        .exclude(status__in=SKIPPED)
        .select_related("competition", "home", "away")
    )


def spend_request(now):
    """Count one request against today's budget. False (and nothing counted) at the daily limit."""
    with transaction.atomic():
        usage, _ = ApiUsage.objects.select_for_update().get_or_create(day=now.date())
        if usage.requests >= settings.LIVE_DAILY_LIMIT:
            return False
        ApiUsage.objects.filter(pk=usage.pk).update(requests=F("requests") + 1)
    return True


def status_of(code):
    if code == "HT":
        return LiveScore.Status.HALF_TIME
    return LiveScore.Status.ENDED if code in ENDED else LiveScore.Status.LIVE


class Runner:
    def __init__(self, client="default", clock=timezone.now, sleep=time.sleep):
        self.client = default_client() if client == "default" else client
        self.clock = clock
        self.sleep = sleep

    def fetch(self, now):
        """{match id: LiveFixture} from one API-Football request, or None when none was made / it failed."""
        if self.client is None or not spend_request(now):
            return None
        try:
            fixtures = self.client.live()
        except ProviderError:
            logger.exception("API-Football live poll failed")
            return None
        competitions = live_matching.competition_ids()
        found = {}
        for fixture in fixtures:
            match = live_matching.find_match(fixture, competitions)
            if match is not None:
                found[match.id] = fixture
        return found

    def target(self, match, fixture, existing, polled):
        """(status, minute, home, away, source) this match should show, or None for 'not live'."""
        api = LiveScore.Source.API_FOOTBALL
        if fixture is not None:
            return (
                status_of(fixture.status),
                fixture.elapsed,
                fixture.home_goals or 0,
                fixture.away_goals or 0,
                api,
            )
        if match.status == Match.Status.FINISHED:
            return None  # football-data has the final score: the match is over
        if match.status in (Match.Status.LIVE, Match.Status.PAUSED):
            status = LiveScore.Status.HALF_TIME if match.status == Match.Status.PAUSED else LiveScore.Status.LIVE
            return (status, None, match.home_score or 0, match.away_score or 0, LiveScore.Source.FOOTBALL_DATA)
        if existing is not None and existing.source == api:
            if polled:  # the API no longer lists it: the whole-match whistle, waiting for football-data
                return (LiveScore.Status.ENDED, existing.minute, existing.home_score, existing.away_score, api)
            return (existing.status, existing.minute, existing.home_score, existing.away_score, api)
        return None

    def apply(self, now, matches, found):
        existing = {row.match_id: row for row in LiveScore.objects.select_related("match")}
        in_window = {match.id for match in matches}
        for match_id, row in existing.items():
            if match_id not in in_window:
                self.remove(row)
        for match in matches:
            row = existing.get(match.id)
            wanted = self.target(match, (found or {}).get(match.id), row, found is not None)
            if wanted is None:
                if row is not None:
                    self.remove(row)
                continue
            self.save(now, match, row, *wanted)

    def remove(self, row):
        match_id = row.match_id
        row.delete()
        feed.publish("remove", {"match": match_id})

    def save(self, now, match, row, status, minute, home, away, source):
        if row is None:
            row = LiveScore(match=match, home_score=home, away_score=away)
            changed = {"new"}
        else:
            changed = set()
            if (row.home_score, row.away_score) != (home, away):
                changed.add("score")
            if row.status != status:
                changed.add("status")
            if row.minute != minute:
                changed.add("minute")
            if row.source != source:
                changed.add("source")
        scored = "score" in changed and home + away > row.home_score + row.away_score
        if not changed:
            return
        row.status, row.minute, row.home_score, row.away_score, row.source = status, minute, home, away, source
        if scored:
            row.goal_at = now
        row.save()
        row.match = match
        data = {**feed.live_data(row), "goal": bool(scored)}
        for event in ("score", "status", "minute"):
            if event in changed or event == "status" and changed & {"new", "source"}:
                feed.publish(event, data)

    def step(self):
        """One tick. Returns the number of matches shown."""
        now = self.clock()
        matches = window_matches(now)
        found = self.fetch(now) if matches else None
        self.apply(now, matches, found)
        return LiveScore.objects.count()

    def run(self):
        while True:
            self.step()
            self.sleep(settings.LIVE_POLL_SECONDS)
