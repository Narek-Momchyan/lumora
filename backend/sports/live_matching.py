"""Which of our Match rows is the match a live provider reports?

A fixture is ours when its league maps to one of our competitions, it kicks off within a few hours
of a match of that competition, and BOTH team names equal ours after normalising. Our names are the
club's name, short name, its translated names and its `TeamAlias(provider="api_football")` rows,
which the admin adds when the two providers spell a club differently ("Wolves" and "Wolverhampton
Wanderers FC"). Anything else is logged and skipped: a wrong match would show a wrong score.
"""

import logging
import unicodedata
from datetime import timedelta

from .models import Competition, Match

logger = logging.getLogger(__name__)

PROVIDER = "api_football"
KICKOFF_TOLERANCE = timedelta(hours=3)
NOISE = {"fc", "afc", "cf", "sc"}  # "Arsenal FC" and "Arsenal" are the same club
OVER = (Match.Status.FINISHED, Match.Status.POSTPONED, Match.Status.CANCELLED, Match.Status.AWARDED)


def normalise(name):
    """"Atlético Madrid" -> "atletico madrid"; "Manchester United FC" -> "manchester united"."""
    plain = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode().lower()
    words = "".join(char if char.isalnum() else " " for char in plain).split()
    return " ".join(word for word in words if word not in NOISE)


def names_of(team):
    """Every normalised name our database knows for the club (names and aliases are prefetched)."""
    names = {team.name, team.short_name}
    names |= {row.name for row in team.names.all()} | {row.short_name for row in team.names.all()}
    names |= {row.name for row in team.aliases.all() if row.provider == PROVIDER}
    return {normalise(name) for name in names if name}


def competition_ids():
    """{API-Football league id: Competition} for the active competitions that have one."""
    rows = Competition.objects.filter(is_active=True, api_football_id__isnull=False)
    return {row.api_football_id: row for row in rows}


def find_match(fixture, competitions):
    """The Match of this LiveFixture, or None (and a log line) when it is not clearly one of ours."""
    competition = competitions.get(fixture.league_id)
    if competition is None:
        return None  # another league: most of live=all, nothing to report
    candidates = (
        Match.objects.filter(
            competition=competition,
            kickoff__gte=fixture.kickoff - KICKOFF_TOLERANCE,
            kickoff__lte=fixture.kickoff + KICKOFF_TOLERANCE,
        )
        .exclude(status__in=OVER)
        .select_related("home", "away")
        .prefetch_related("home__names", "home__aliases", "away__names", "away__aliases")
    )
    home, away = normalise(fixture.home), normalise(fixture.away)
    found = [match for match in candidates if home in names_of(match.home) and away in names_of(match.away)]
    if len(found) == 1:
        return found[0]
    logger.warning(
        "unmatched_live_fixture: %s – %s (%s, %s, fixture %s): %s",
        fixture.home,
        fixture.away,
        competition.code,
        fixture.kickoff.isoformat(),
        fixture.provider_id,
        "several matches fit" if found else "no club of ours has these names; add a TeamAlias for api_football",
    )
    return None
