from datetime import date

from django.db.models import Prefetch
from rest_framework.permissions import AllowAny

from base.language import get_lang
from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from .models import Competition, Match, Season, SportsPageLabel, Standing, Team
from .serializers import (
    CompetitionSerializer,
    MatchSerializer,
    SportsPageLabelSerializer,
    StandingSerializer,
    TeamSerializer,
)

TEAMS = Team.objects.prefetch_related("names")


class SportsPageLabelViewSet(LangFilteredViewSet):
    queryset = SportsPageLabel.objects.all()
    serializer_class = SportsPageLabelSerializer


class FootballViewSet(FilteredReadOnlyViewSet):
    """Public football data from our database (the browser never calls a provider). Names in ?lang=."""

    permission_classes = [AllowAny]

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": get_lang(self.request)}


class CompetitionViewSet(FootballViewSet):
    queryset = Competition.objects.filter(is_active=True).prefetch_related(
        "names", Prefetch("seasons", queryset=Season.objects.filter(is_current=True))
    )
    serializer_class = CompetitionSerializer


class TeamViewSet(FootballViewSet):
    """?competition=PL: the clubs of one competition."""

    queryset = TEAMS
    serializer_class = TeamSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        code = self.request.query_params.get("competition")
        return qs.filter(competitions__code=code).distinct() if code else qs


class MatchViewSet(FootballViewSet):
    """?competition=PL, ?date=2026-11-08 (a UTC day), ?status=finished, ?team=<id>."""

    queryset = Match.objects.filter(competition__is_active=True).select_related("competition").prefetch_related(
        Prefetch("home", queryset=TEAMS), Prefetch("away", queryset=TEAMS)
    )
    serializer_class = MatchSerializer
    filter_fields = ("status",)
    list_limit = 300

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if "competition" in params:
            qs = qs.filter(competition__code=params["competition"])
        if "team" in params:
            team = params["team"]
            if not team.isdigit():
                return qs.none()
            qs = qs.filter(home_id=team) | qs.filter(away_id=team)
        if "date" in params:
            try:
                day = date.fromisoformat(params["date"])
            except ValueError:
                return qs.none()  # an unknown filter value is an empty list, like any filter
            qs = qs.filter(kickoff__date=day)
        return qs


class StandingViewSet(FootballViewSet):
    """?competition=PL: the current season's tables (a Champions League group per `group`)."""

    queryset = Standing.objects.filter(season__is_current=True, season__competition__is_active=True).prefetch_related(
        Prefetch("team", queryset=TEAMS)
    )
    serializer_class = StandingSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        code = self.request.query_params.get("competition")
        return qs.filter(season__competition__code=code) if code else qs
