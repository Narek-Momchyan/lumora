from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from base.language import get_lang
from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from errors.exceptions import CodedError
from wallet.models import Wallet
from wallet.services import InsufficientFunds
from . import betting
from .models import (
    Bet,
    BetLabel,
    Competition,
    Market,
    Match,
    Season,
    Selection,
    SportsPageLabel,
    Standing,
    Team,
)
from .serializers import (
    BetLabelSerializer,
    BetRequestSerializer,
    BetSerializer,
    CompetitionSerializer,
    MarketSerializer,
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


class BetLabelViewSet(LangFilteredViewSet):
    queryset = BetLabel.objects.all()
    serializer_class = BetLabelSerializer


class MarketViewSet(FootballViewSet):
    """?match=<id>: the match's markets with their odds, the previous odds and the model's probability."""

    queryset = Market.objects.prefetch_related(Prefetch("selections", queryset=Selection.objects.order_by("id")))
    serializer_class = MarketSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        match = self.request.query_params.get("match")
        if match is None:
            return qs.filter(status=Market.Status.OPEN)
        return qs.filter(match_id=match) if match.isdigit() else qs.none()


BET_MATCHES = Match.objects.select_related("competition").prefetch_related(
    Prefetch("home", queryset=TEAMS), Prefetch("away", queryset=TEAMS)
)


class SportBetViewSet(FilteredReadOnlyViewSet):
    """GET: my bets (?status=open|won|lost|void|settled). POST {key, stake, selections: [{selection, odds}]}."""

    queryset = Bet.objects.prefetch_related("picks__selection__market", Prefetch("picks__match", queryset=BET_MATCHES))
    serializer_class = BetSerializer
    list_limit = 100

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": get_lang(self.request)}

    def get_queryset(self):
        qs = super().get_queryset().filter(user=self.request.user)
        wanted = self.request.query_params.get("status")
        if wanted == "settled":
            return qs.exclude(status=Bet.Status.OPEN)
        if wanted is not None:
            return qs.filter(status=wanted)
        return qs

    def create(self, request, *args, **kwargs):
        serializer = BetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        picks = [betting.Pick(pick["selection"], pick["odds"]) for pick in data["selections"]]
        try:
            bet, created = betting.place_bet(request.user, data["key"], data["stake"], picks)
        except InsufficientFunds as exc:
            raise CodedError("not_enough_lc", "Not enough LC.") from exc
        except betting.BetError as exc:
            raise CodedError(exc.code, str(exc), status_code=exc.status_code, extra=exc.extra, **exc.params) from exc
        bet = self.get_queryset().get(pk=bet.pk)
        balance = Wallet.objects.values_list("balance", flat=True).get(user=request.user)
        return Response(
            {**self.get_serializer(bet).data, "balance": str(balance)},
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    @action(detail=False)
    def summary(self, request):
        """The last 7 days for My bets (design 08): staked, returned, profit, won and open bets."""
        bets = list(Bet.objects.filter(user=request.user, created_at__gte=timezone.now() - timedelta(days=7)))
        settled = [bet for bet in bets if bet.status != Bet.Status.OPEN]
        staked = sum((bet.stake for bet in bets), Decimal("0.00"))
        returned = sum((bet.payout for bet in settled), Decimal("0.00"))
        settled_stake = sum((bet.stake for bet in settled), Decimal("0.00"))
        return Response(
            {
                "staked": str(staked),
                "returned": str(returned),
                "profit": str(returned - settled_stake),
                "won": sum(1 for bet in bets if bet.status == Bet.Status.WON),
                "open": len(bets) - len(settled),
                "bets": len(bets),
            }
        )
