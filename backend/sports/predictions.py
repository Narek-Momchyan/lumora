"""Free score predictions: saving them until kickoff, scoring them after full time, the leaderboards.

No LC moves here (Rule 1). A prediction is scored only from the regular-time score of a FINISHED
match, in an idempotent job that runs after every football sync, right after bets are settled.
"""

from django.db import transaction
from django.db.models import Count, Min, Q, Sum
from django.utils import timezone

from base import names
from errors.exceptions import CodedError
from . import betting
from .models import Match, Prediction

EXACT_POINTS = 3
RESULT_POINTS = 1
MAX_GOALS = 20
INVALID = "A prediction is two whole numbers from 0 to {max}."
SCORED = [Prediction.Outcome.EXACT, Prediction.Outcome.RESULT, Prediction.Outcome.WRONG]


def sign(home, away):
    return (home > away) - (home < away)


def score(pred_home, pred_away, real_home, real_away):
    """(points, outcome): 3 for the exact score, 1 for the right result, else 0."""
    if (pred_home, pred_away) == (real_home, real_away):
        return EXACT_POINTS, Prediction.Outcome.EXACT
    if sign(pred_home, pred_away) == sign(real_home, real_away):
        return RESULT_POINTS, Prediction.Outcome.RESULT
    return 0, Prediction.Outcome.WRONG


def is_open(match, now):
    return match.status == Match.Status.SCHEDULED and match.kickoff > now


def check_goals(value):
    if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= MAX_GOALS:
        raise CodedError("prediction_invalid", INVALID, max=MAX_GOALS)


def save_predictions(user, items, now=None):
    """Save [(match_id, home, away)] in one transaction: all or nothing. Returns [(prediction, created)]."""
    now = now or timezone.now()
    for _, home, away in items:
        check_goals(home)
        check_goals(away)
    ids = [match_id for match_id, _, _ in items]
    if len(set(ids)) != len(ids):
        raise CodedError("prediction_invalid", INVALID, max=MAX_GOALS)
    saved = []
    with transaction.atomic():
        matches = {m.id: m for m in Match.objects.select_for_update().filter(id__in=ids).order_by("id")}
        for match_id, home, away in items:
            match = matches.get(match_id)
            if match is None:
                raise CodedError("match_not_found", "This match does not exist.", status_code=404)
            if not is_open(match, now):
                raise CodedError("prediction_locked", "Predictions for this match closed at kickoff.")
            prediction, created = Prediction.objects.update_or_create(
                user=user, match=match, defaults={"home_goals": home, "away_goals": away}
            )
            saved.append((prediction, created))
    return saved


def score_predictions(now=None):
    """Score every pending prediction of a decided match. Safe to run again: scored rows are skipped."""
    now = now or timezone.now()
    done = 0
    for prediction in Prediction.objects.filter(outcome=Prediction.Outcome.PENDING).select_related("match"):
        match = prediction.match
        if betting.is_void(match, now):
            points, outcome = 0, Prediction.Outcome.VOID
        elif match.status == Match.Status.FINISHED and match.home_regular is not None and match.away_regular is not None:
            points, outcome = score(prediction.home_goals, prediction.away_goals, match.home_regular, match.away_regular)
        else:
            continue
        with transaction.atomic():
            row = Prediction.objects.select_for_update().get(pk=prediction.pk)
            if row.outcome != Prediction.Outcome.PENDING:
                continue  # another run scored it while we waited for the lock
            row.outcome, row.points, row.scored_at = outcome, points, now
            row.save(update_fields=["outcome", "points", "scored_at"])
        done += 1
    return done


def board(competition, matchday=None):
    """Every player's totals in a league's current season (or one matchday), best first.

    Order: points, then exact scores, then who predicted earlier (first save), then user id.
    """
    rows = Prediction.objects.filter(
        outcome__in=SCORED, match__competition=competition, match__season__is_current=True
    )
    if matchday is not None:
        rows = rows.filter(match__matchday=matchday)
    rows = (
        rows.values("user_id", "user__display_name")
        .annotate(
            points=Sum("points"),
            exact=Count("id", filter=Q(outcome=Prediction.Outcome.EXACT)),
            right=Count("id", filter=Q(outcome__in=[Prediction.Outcome.EXACT, Prediction.Outcome.RESULT])),
            played=Count("id"),
            first=Min("created_at"),
        )
        .order_by("-points", "-exact", "first", "user_id")
    )
    return [
        {
            "rank": rank,
            "user_id": row["user_id"],
            "player": names.public_name(row["user__display_name"], row["user_id"]),
            "points": row["points"],
            "exact": row["exact"],
            "right": row["right"],
            "played": row["played"],
        }
        for rank, row in enumerate(rows, start=1)
    ]


def public_row(row, user):
    """A board row as the API sends it: no user id (it is sequential), `is_me` says which row is the viewer's."""
    shown = {key: value for key, value in row.items() if key != "user_id"}
    return {**shown, "is_me": user is not None and row["user_id"] == user.id}


def leaderboard(competition, matchday=None, user=None, limit=6):
    """{"players", "rows" (the top `limit`), "me" (my row with my rank, or None)}; rows carry no user id."""
    table = board(competition, matchday)
    me = next((row for row in table if user is not None and row["user_id"] == user.id), None)
    return {
        "players": len(table),
        "rows": [public_row(row, user) for row in table[:limit]],
        "me": public_row(me, user) if me else None,
    }


def my_stats(user, competition):
    """My points, rank and shares in the league's current season; zeros before the first scored match."""
    table = board(competition)
    me = next((row for row in table if row["user_id"] == user.id), None)
    if me is None:
        return {"points": 0, "rank": None, "exact": 0, "right_percent": 0, "played": 0, "players": len(table)}
    return {
        "points": me["points"],
        "rank": me["rank"],
        "exact": me["exact"],
        "right_percent": round(100 * me["right"] / me["played"]),
        "played": me["played"],
        "players": len(table),
    }
