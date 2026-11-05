"""The football sync: provider data (sports.providers) into our tables.

Every row is found by the provider's id and updated in place, so running a sync twice changes
nothing the second time. One competition is one transaction; an error in one competition is
written to its SyncRun and the others go on.
"""

import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .models import Competition, Match, Season, Standing, SyncRun, Team
from .providers.crests import badge_colours, crest_file
from .providers.football_data import FootballDataClient

logger = logging.getLogger(__name__)


@dataclass
class Counts:
    created: int = 0
    updated: int = 0
    errors: list[str] = field(default_factory=list)

    def add(self, was_created):
        if was_created:
            self.created += 1
        else:
            self.updated += 1


def default_client():
    token = settings.FOOTBALL_DATA_TOKEN
    if not token:
        raise RuntimeError("Set FOOTBALL_DATA_TOKEN in backend/.env to sync football data.")
    return FootballDataClient(token, base_url=settings.FOOTBALL_DATA_URL)


def upsert(model, lookup, values, counts):
    """update_or_create that counts a row as updated only when a value really changed."""
    row = model.objects.filter(**lookup).first()
    if row is None:
        counts.add(True)
        return model.objects.create(**lookup, **values)
    changed = [name for name, value in values.items() if getattr(row, name) != value]
    if changed:
        for name in changed:
            setattr(row, name, values[name])
        row.save(update_fields=changed)
        counts.add(False)
    return row


def save_team(client, data, competition, counts):
    team = Team.objects.filter(provider_id=data.provider_id).first()
    values = {"name": data.name, "short_name": data.short_name, "tla": data.tla}
    if team is None:
        colours = badge_colours(data.club_colors)
        if colours:
            values["color"], values["text_color"] = colours
    team = upsert(Team, {"provider_id": data.provider_id}, values, counts)
    team.competitions.add(competition)
    save_crest(client, team, data.crest_url, counts)
    return team


def save_crest(client, team, url, counts):
    """Downloads the crest once per URL. A crest uploaded in the admin is never replaced."""
    if not url or team.crest_locked or team.crest_source_url == url:
        return
    try:
        file = crest_file(url, client.download(url))
    except Exception as exc:  # a missing crest only means the initials badge is shown
        counts.errors.append(f"crest {team.name}: {exc}")
        return
    if file is None:
        counts.errors.append(f"crest {team.name}: not a usable image")
        return
    if team.crest:
        team.crest.delete(save=False)
    team.crest.save(file.name, file, save=False)
    team.crest_source_url = url
    team.save(update_fields=["crest", "crest_source_url"])


def match_values(data, competition, season, home, away):
    return {
        "competition": competition,
        "season": season,
        "matchday": data.matchday,
        "stage": data.stage,
        "group": data.group,
        "home": home,
        "away": away,
        "kickoff": data.kickoff,
        "status": data.status,
        "provider_status": data.provider_status,
        "duration": data.duration,
        "home_score": data.full_time.home,
        "away_score": data.full_time.away,
        "home_half": data.half_time.home,
        "away_half": data.half_time.away,
        "home_regular": data.regular_time.home,
        "away_regular": data.regular_time.away,
        "home_extra": data.extra_time.home,
        "away_extra": data.extra_time.away,
        "home_penalties": data.penalties.home,
        "away_penalties": data.penalties.away,
        "provider_updated": data.provider_updated,
    }


def sync_competition(client, competition, kind, today=None):
    """Season, teams, matches and table of one competition. Returns the run's Counts."""
    counts = Counts()
    today = today or timezone.now().date()

    with transaction.atomic():
        info = client.competition(competition.code)
        if competition.provider_id != info.provider_id:
            competition.provider_id = info.provider_id
            competition.save(update_fields=["provider_id"])

        season = upsert(
            Season,
            {"provider_id": info.season.provider_id},
            {
                "competition": competition,
                "start_date": info.season.start_date,
                "end_date": info.season.end_date,
                "current_matchday": info.season.current_matchday,
                "is_current": True,
            },
            counts,
        )
        Season.objects.filter(competition=competition, is_current=True).exclude(pk=season.pk).update(is_current=False)

        teams = {}
        if kind == SyncRun.Kind.FULL:
            for data in client.teams(competition.code):
                teams[data.provider_id] = save_team(client, data, competition, counts)
            matches = client.matches(competition.code)
        else:
            matches = client.matches(competition.code, today - timedelta(days=1), today + timedelta(days=1))

        for data in matches:
            home = teams.get(data.home.provider_id) or save_team(client, data.home, competition, counts)
            away = teams.get(data.away.provider_id) or save_team(client, data.away, competition, counts)
            teams[home.provider_id], teams[away.provider_id] = home, away
            match_season = season if data.season_id == season.provider_id else Season.objects.get(provider_id=data.season_id)
            upsert(Match, {"provider_id": data.provider_id}, match_values(data, competition, match_season, home, away), counts)

        for row in client.standings(competition.code):
            team = teams.get(row.team_id) or Team.objects.filter(provider_id=row.team_id).first()
            if team is None:
                counts.errors.append(f"standing: unknown team {row.team_id}")
                continue
            upsert(
                Standing,
                {"season": season, "stage": row.stage, "group": row.group, "type": row.type, "team": team},
                {
                    "position": row.position,
                    "played": row.played,
                    "won": row.won,
                    "draw": row.draw,
                    "lost": row.lost,
                    "goals_for": row.goals_for,
                    "goals_against": row.goals_against,
                    "goal_difference": row.goal_difference,
                    "points": row.points,
                    "form": row.form,
                },
                counts,
            )
    return counts


def run_sync(client=None, kind=SyncRun.Kind.TODAY, codes=None, today=None):
    """Sync the active competitions (or `codes`), one SyncRun per competition."""
    client = client or default_client()
    competitions = Competition.objects.filter(is_active=True)
    if codes:
        competitions = competitions.filter(code__in=codes)

    runs = []
    for competition in competitions:
        run = SyncRun.objects.create(kind=kind, competition=competition)
        before = client.requests
        try:
            counts = sync_competition(client, competition, kind, today=today)
            run.created, run.updated = counts.created, counts.updated
            run.errors = "\n".join(counts.errors)
            run.ok = True
        except Exception as exc:
            logger.exception("Football sync of %s failed", competition.code)
            run.errors = f"{type(exc).__name__}: {exc}"
        run.requests = client.requests - before
        run.finished_at = timezone.now()
        run.save()
        runs.append(run)
    return runs


def has_matches_today(today=None):
    """Whether any of our matches kicks off today (UTC), so the runner syncs every few minutes."""
    today = today or timezone.now().date()
    return Match.objects.filter(competition__is_active=True, kickoff__date=today).exists()
