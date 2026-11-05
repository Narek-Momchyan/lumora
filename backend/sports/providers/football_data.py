"""football-data.org v4 (https://docs.football-data.org/general/v4/index.html).

The free plan: our six competitions, 10 requests a minute, scores and schedules delayed. The token
goes in the X-Auth-Token header. The server reports the requests left in X-RequestsAvailable and
the seconds until the counter resets in X-RequestCounter-Reset; on 429 we wait that long.
"""

from datetime import date

import httpx
from django.utils.dateparse import parse_date, parse_datetime

from .base import CompetitionData, MatchData, Score, SeasonData, StandingData, TeamData
from .rate_limit import RateLimiter

TIMEOUT_SECONDS = 15
MAX_ATTEMPTS = 4
DEFAULT_RESET_SECONDS = 60
SERVER_ERROR_BACKOFF_SECONDS = 5
CRESTS_PER_MINUTE = 60  # crests.football-data.org is a static host, outside the API's limit

# Provider status → sports.models.Match.Status. Extra time and the shootout are still "live".
STATUSES = {
    "SCHEDULED": "scheduled",
    "TIMED": "scheduled",
    "IN_PLAY": "live",
    "EXTRA_TIME": "live",
    "PENALTY_SHOOTOUT": "live",
    "PAUSED": "paused",
    "FINISHED": "finished",
    "AWARDED": "awarded",
    "POSTPONED": "postponed",
    "SUSPENDED": "suspended",
    "CANCELLED": "cancelled",
}


class ProviderError(Exception):
    pass


def score(data):
    data = data or {}
    return Score(data.get("home"), data.get("away"))


def regular_time(raw):
    """The score after 90 minutes + stoppage, which bets are settled on.

    A REGULAR match: the full-time score. A match with extra time: `regularTime` when the provider
    sends it, else full time minus extra time. Unknown (None, None) until there is a number.
    """
    full = score(raw.get("fullTime"))
    if raw.get("duration", "REGULAR") == "REGULAR":
        return full
    if raw.get("regularTime"):
        return score(raw["regularTime"])
    extra = score(raw.get("extraTime"))
    if None in (full.home, full.away, extra.home, extra.away):
        return Score(None, None)
    return Score(full.home - extra.home, full.away - extra.away)


def team(raw):
    return TeamData(
        provider_id=raw["id"],
        name=raw.get("name") or "",
        short_name=raw.get("shortName") or "",
        tla=raw.get("tla") or "",
        crest_url=raw.get("crest") or "",
        club_colors=raw.get("clubColors") or "",
    )


def match(raw):
    result = raw.get("score") or {}
    status = raw["status"]
    if status not in STATUSES:
        raise ProviderError(f"Unknown match status {status!r}")
    return MatchData(
        provider_id=raw["id"],
        season_id=raw["season"]["id"],
        matchday=raw.get("matchday"),
        stage=raw.get("stage") or "",
        group=raw.get("group") or "",
        home=team(raw["homeTeam"]),
        away=team(raw["awayTeam"]),
        kickoff=parse_datetime(raw["utcDate"]),
        status=STATUSES[status],
        provider_status=status,
        duration=result.get("duration") or "",
        full_time=score(result.get("fullTime")),
        half_time=score(result.get("halfTime")),
        regular_time=regular_time(result),
        extra_time=score(result.get("extraTime")),
        penalties=score(result.get("penalties")),
        provider_updated=parse_datetime(raw["lastUpdated"]) if raw.get("lastUpdated") else None,
    )


def standings(raw):
    rows = []
    for table in raw.get("standings", []):
        for row in table.get("table", []):
            rows.append(
                StandingData(
                    stage=table.get("stage") or "",
                    group=table.get("group") or "",
                    type=table.get("type") or "TOTAL",
                    team_id=row["team"]["id"],
                    position=row["position"],
                    played=row.get("playedGames", 0),
                    won=row.get("won", 0),
                    draw=row.get("draw", 0),
                    lost=row.get("lost", 0),
                    goals_for=row.get("goalsFor", 0),
                    goals_against=row.get("goalsAgainst", 0),
                    goal_difference=row.get("goalDifference", 0),
                    points=row.get("points", 0),
                    form=row.get("form") or "",
                )
            )
    return rows


class FootballDataClient:
    def __init__(self, token, base_url="https://api.football-data.org/v4", transport=None, limiter=None):
        self.limiter = limiter or RateLimiter(per_minute=10)
        self.crest_limiter = RateLimiter(CRESTS_PER_MINUTE, clock=self.limiter.clock, sleep=self.limiter.sleep)
        self.requests = 0
        self.http = httpx.Client(
            base_url=base_url.rstrip("/") + "/",
            headers={"X-Auth-Token": token},
            timeout=TIMEOUT_SECONDS,
            transport=transport,
        )
        # Crests come from another host: no token goes there.
        self.crest_http = httpx.Client(timeout=TIMEOUT_SECONDS, transport=transport, follow_redirects=True)

    def get(self, path, params=None):
        return self.fetch(self.http, self.limiter, path, params).json()

    def fetch(self, http, limiter, url, params=None):
        """One request through the rate limiter, waiting and retrying on 429 and 5xx."""
        for attempt in range(1, MAX_ATTEMPTS + 1):
            limiter.wait()
            self.requests += 1
            try:
                response = http.get(url, params=params)
            except httpx.TransportError as exc:
                if attempt == MAX_ATTEMPTS:
                    raise ProviderError(f"{url}: {exc}") from exc
                limiter.pause(SERVER_ERROR_BACKOFF_SECONDS * attempt)
                continue
            if response.status_code == 429:
                reset = response.headers.get("X-RequestCounter-Reset", "")
                limiter.pause(int(reset) + 1 if reset.isdigit() else DEFAULT_RESET_SECONDS)
                continue
            if response.status_code >= 500 and attempt < MAX_ATTEMPTS:
                limiter.pause(SERVER_ERROR_BACKOFF_SECONDS * attempt)
                continue
            if response.status_code >= 400:
                raise ProviderError(f"{url}: HTTP {response.status_code}")
            return response
        raise ProviderError(f"{url}: still limited after {MAX_ATTEMPTS} attempts")

    def competition(self, code):
        raw = self.get(f"competitions/{code}")
        season = raw["currentSeason"]
        return CompetitionData(
            provider_id=raw["id"],
            code=raw["code"],
            name=raw["name"],
            season=SeasonData(
                provider_id=season["id"],
                start_date=parse_date(season["startDate"]),
                end_date=parse_date(season["endDate"]),
                current_matchday=season.get("currentMatchday"),
            ),
        )

    def teams(self, code):
        return [team(raw) for raw in self.get(f"competitions/{code}/teams").get("teams", [])]

    def matches(self, code, date_from: date | None = None, date_to: date | None = None):
        params = {}
        if date_from:
            params["dateFrom"] = date_from.isoformat()
        if date_to:
            params["dateTo"] = date_to.isoformat()
        return [match(raw) for raw in self.get(f"competitions/{code}/matches", params).get("matches", [])]

    def standings(self, code):
        return standings(self.get(f"competitions/{code}/standings"))

    def download(self, url):
        """A crest image from crests.football-data.org."""
        return self.fetch(self.crest_http, self.crest_limiter, url).content

    def close(self):
        self.http.close()
        self.crest_http.close()
