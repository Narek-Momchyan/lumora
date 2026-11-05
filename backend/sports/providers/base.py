"""What the sync needs from a football provider. A paid live feed can replace football-data.org
later by returning the same dataclasses; the sync never sees a provider's JSON."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol


@dataclass(frozen=True)
class SeasonData:
    provider_id: int
    start_date: date
    end_date: date
    current_matchday: int | None


@dataclass(frozen=True)
class CompetitionData:
    provider_id: int
    code: str
    name: str
    season: SeasonData


@dataclass(frozen=True)
class TeamData:
    provider_id: int
    name: str
    short_name: str
    tla: str
    crest_url: str
    club_colors: str


@dataclass(frozen=True)
class Score:
    home: int | None
    away: int | None


@dataclass(frozen=True)
class MatchData:
    provider_id: int
    season_id: int
    matchday: int | None
    stage: str
    group: str
    home: TeamData  # a match carries its teams, so a team missing from /teams is still known
    away: TeamData
    kickoff: datetime
    status: str  # one of sports.models.Match.Status
    provider_status: str
    duration: str
    full_time: Score
    half_time: Score
    regular_time: Score  # (None, None) until it is known
    extra_time: Score
    penalties: Score
    provider_updated: datetime | None


@dataclass(frozen=True)
class StandingData:
    stage: str
    group: str
    type: str
    team_id: int
    position: int
    played: int
    won: int
    draw: int
    lost: int
    goals_for: int
    goals_against: int
    goal_difference: int
    points: int
    form: str


@dataclass(frozen=True)
class LiveFixture:
    """One match that is being played right now, from a live-score provider (display only)."""

    provider_id: int
    league_id: int  # the provider's own league id
    kickoff: datetime
    home: str  # team names as the provider spells them
    away: str
    home_goals: int | None
    away_goals: int | None
    elapsed: int | None  # the match minute
    status: str  # the provider's short code: 1H, HT, 2H, ET, P, FT ...


class LiveProvider(Protocol):
    """What the live poller needs: one call with every match in play. A paid feed can replace
    API-Football by returning the same dataclass."""

    requests: int

    def live(self) -> list[LiveFixture]: ...


class FootballProvider(Protocol):
    requests: int  # how many HTTP requests it made, for SyncRun

    def competition(self, code: str) -> CompetitionData: ...

    def teams(self, code: str) -> list[TeamData]: ...

    def matches(self, code: str, date_from: date | None = None, date_to: date | None = None) -> list[MatchData]: ...

    def standings(self, code: str) -> list[StandingData]: ...

    def download(self, url: str) -> bytes: ...
