"""API-Football v3 (https://www.api-football.com/documentation-v3), free plan: 100 requests a day.

Only one call is used: `fixtures?live=all`, every match in play now. The free plan blocks the
fixture lists of the current season but answers this one, with current-season data. The key goes
in the x-apisports-key header. What this returns is shown on the live page and never settles a
bet or a prediction (design/sports-spec.md section 2).
"""

import httpx
from django.utils.dateparse import parse_datetime

from .base import LiveFixture
from .football_data import ProviderError

TIMEOUT_SECONDS = 15
BASE_URL = "https://v3.football.api-sports.io"


def fixture(raw):
    """One entry of the `response` list -> LiveFixture."""
    info, league, teams, goals = raw["fixture"], raw["league"], raw["teams"], raw.get("goals") or {}
    status = info.get("status") or {}
    return LiveFixture(
        provider_id=info["id"],
        league_id=league["id"],
        kickoff=parse_datetime(info["date"]),
        home=teams["home"]["name"],
        away=teams["away"]["name"],
        home_goals=goals.get("home"),
        away_goals=goals.get("away"),
        elapsed=status.get("elapsed"),
        status=status.get("short") or "",
    )


def fixtures(payload):
    """The whole answer -> [LiveFixture]. A body with `errors` (a bad key, a plan limit) is an error."""
    errors = payload.get("errors")
    if errors:  # the API sends [] when fine and an object or a list of messages when not
        raise ProviderError(f"API-Football: {errors}")
    return [fixture(row) for row in payload.get("response", [])]


class ApiFootballClient:
    def __init__(self, key, base_url=BASE_URL, transport=None):
        self.requests = 0
        self.remaining = None  # requests left today, as the server counts them
        self.http = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers={"x-apisports-key": key},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )

    def live(self):
        self.requests += 1
        try:
            response = self.http.get("fixtures", params={"live": "all"})
        except httpx.TransportError as exc:
            raise ProviderError(f"API-Football: {exc}") from exc
        if response.status_code >= 400:
            raise ProviderError(f"API-Football: HTTP {response.status_code}")
        remaining = response.headers.get("x-ratelimit-requests-remaining")
        self.remaining = int(remaining) if remaining and remaining.isdigit() else None
        return fixtures(response.json())

    def close(self):
        self.http.close()
