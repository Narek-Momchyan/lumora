"""Turns the model into markets: fit on finished matches, price the next 14 days, freeze at kickoff."""

from datetime import timedelta
from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from . import engine
from .models import Market, Match, ModelRun, Selection

PRICE_AHEAD = timedelta(days=14)
PROBABILITY_PLACES = Decimal("0.0001")


def finished_results():
    """Every finished match with a known regular-time score, as the engine's Results."""
    rows = (
        Match.objects.filter(status=Match.Status.FINISHED, home_regular__isnull=False, away_regular__isnull=False)
        .select_related("competition")
        .order_by("kickoff")
    )
    return [
        engine.Result(m.competition.code, m.home_id, m.away_id, m.home_regular, m.away_regular, m.kickoff.date())
        for m in rows
    ]


def close_started_markets(now):
    """Kickoff passed: the odds are frozen and nobody can bet any more."""
    return Market.objects.filter(status=Market.Status.OPEN, match__kickoff__lte=now).update(
        status=Market.Status.CLOSED
    )


def refresh_odds(now=None):
    """Fit the model and price every scheduled match of the next 14 days. Returns the ModelRun."""
    now = now or timezone.now()
    close_started_markets(now)

    ratings = engine.fit(finished_results(), now.date())
    upcoming = Match.objects.filter(
        status=Match.Status.SCHEDULED, kickoff__gt=now, kickoff__lte=now + PRICE_AHEAD, competition__is_active=True
    ).select_related("competition")

    priced = 0
    for match in upcoming:
        price_match(match, ratings, now)
        priced += 1

    return ModelRun.objects.create(
        matches_used=ratings.matches, rho=ratings.rho, params=ratings.as_dict(), priced_matches=priced
    )


def price_match(match, ratings, now):
    odds = engine.match_odds(ratings, match.competition.code, match.home_id, match.away_id)
    with transaction.atomic():
        # Lock order everywhere: selection rows before the wallet (see sports/betting.py).
        markets = {}
        for (kind, line, code), (probability, price) in odds.items():
            key = (kind, line)
            if key not in markets:
                market, _ = Market.objects.get_or_create(match=match, kind=kind, line=line)
                markets[key] = market
            market = markets[key]
            if market.status != Market.Status.OPEN:
                continue  # frozen at kickoff, or already settled
            if market.match.kickoff <= now:
                continue
            fair = Decimal(probability).quantize(PROBABILITY_PLACES)
            selection = Selection.objects.select_for_update().filter(market=market, code=code).first()
            if selection is None:
                Selection.objects.create(market=market, code=code, odds=price, probability=fair)
            elif selection.odds != price or selection.probability != fair:
                if selection.odds != price:
                    selection.previous_odds = selection.odds  # for the ▲ / ▼ in the frontend
                selection.odds = price
                selection.probability = fair
                selection.save(update_fields=["odds", "previous_odds", "probability"])
