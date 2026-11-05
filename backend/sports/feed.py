"""What the /ws/sports clients see: the matches being played now. Public and read-only.

Everything is plain strings and numbers (the channel layer carries msgpack). A club's crest is the
relative /media path, which the site serves through its own /media rewrite. Names are the provider's
English ones; the live page shows its own translated names from /api/live_matches.
"""

from django.utils import timezone

from base import live
from .models import LiveScore

GROUP = "sports"


def publish(event, data):
    live.publish(GROUP, event, data)


def _time(value):
    return value.isoformat() if value else None


def team_data(team):
    return {
        "id": team.id,
        "name": team.name,
        "short_name": team.short_name,
        "tla": team.tla,
        "color": team.color,
        "text_color": team.text_color,
        "crest": team.crest.url if team.crest else None,
    }


def live_data(row):
    """One match in play, whole: a client replaces what it had with this."""
    match = row.match
    return {
        "match": match.id,
        "competition": match.competition.code,
        "kickoff": _time(match.kickoff),
        "home": team_data(match.home),
        "away": team_data(match.away),
        "status": row.status,
        "minute": row.minute,
        "home_score": row.home_score,
        "away_score": row.away_score,
        "source": row.source,
        "delayed": row.source == LiveScore.Source.FOOTBALL_DATA,
        "goal_at": _time(row.goal_at),
        "updated_at": _time(row.updated_at),
    }


def snapshot():
    """Every match in play, sent once to each new client."""
    rows = LiveScore.objects.select_related("match__competition", "match__home", "match__away")
    return {"matches": [live_data(row) for row in rows], "server_time": _time(timezone.now())}
