from datetime import date, timedelta
from decimal import Decimal

from django.db.models import Count, Prefetch
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework import viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from base.language import get_lang
from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from errors.exceptions import CodedError
from wallet.models import Wallet
from wallet.services import InsufficientFunds
from . import betting, predictions
from .models import (
    Bet,
    BetLabel,
    Competition,
    LiveLabel,
    LiveScore,
    Market,
    Match,
    Prediction,
    PredictionLabel,
    Season,
    Selection,
    SportsPageLabel,
    SportsUiLabel,
    Standing,
    StandingZone,
    Team,
)
from .serializers import (
    BetLabelSerializer,
    BetRequestSerializer,
    BetSerializer,
    BulkPredictionRequestSerializer,
    LiveLabelSerializer,
    LiveScoreSerializer,
    CompetitionSerializer,
    MarketSerializer,
    MatchDetailSerializer,
    PopularPickSerializer,
    PredictionLabelSerializer,
    PredictionRequestSerializer,
    PredictionSerializer,
    StandingZoneSerializer,
    SportsUiLabelSerializer,
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

    queryset = (
        Match.objects.filter(competition__is_active=True)
        .annotate(market_count=Count("markets"))
        .select_related("competition")
        .prefetch_related(Prefetch("home", queryset=TEAMS), Prefetch("away", queryset=TEAMS))
    )
    serializer_class = MatchSerializer
    filter_fields = ("status",)
    list_limit = 300

    def get_serializer_class(self):
        return MatchDetailSerializer if self.action == "retrieve" else MatchSerializer

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
    """?match=1,2: those matches' markets; ?date=2026-11-08 (a UTC day); ?kind=1x2. With none of the
    first two, every open market. Each selection has its odds, previous odds and the model's probability."""

    queryset = Market.objects.prefetch_related(Prefetch("selections", queryset=Selection.objects.order_by("id")))
    serializer_class = MarketSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if "kind" in params:
            qs = qs.filter(kind=params["kind"])
        if "date" in params:
            try:
                return qs.filter(match__kickoff__date=date.fromisoformat(params["date"]))
            except ValueError:
                return qs.none()
        if "match" in params:
            ids = params["match"].split(",")
            if not all(part.isdigit() for part in ids):
                return qs.none()
            return qs.filter(match_id__in=ids)
        return qs.filter(status=Market.Status.OPEN)


BET_MATCHES = Match.objects.select_related("competition").prefetch_related(
    Prefetch("home", queryset=TEAMS), Prefetch("away", queryset=TEAMS)
)


def profit_by_day(user, days=7):
    """The last 7 days (UTC, oldest first): what the bets settled that day returned minus their stakes."""
    today = timezone.now().date()
    totals = {today - timedelta(days=offset): Decimal("0.00") for offset in range(days)}
    settled = Bet.objects.filter(user=user, settled_at__date__gte=min(totals)).exclude(status=Bet.Status.OPEN)
    for bet in settled:
        day = bet.settled_at.date()
        if day in totals:
            totals[day] += bet.payout - bet.stake
    return [{"date": day.isoformat(), "profit": str(totals[day])} for day in sorted(totals)]


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
                "by_day": profit_by_day(request.user),
            }
        )


class SportsUiLabelViewSet(LangFilteredViewSet):
    queryset = SportsUiLabel.objects.all()
    serializer_class = SportsUiLabelSerializer


class PopularPickViewSet(FootballViewSet):
    """The three open picks most bets of the last 7 days contain. Empty until players have bet."""

    serializer_class = PopularPickSerializer
    list_limit = 3

    def get_queryset(self):
        now = timezone.now()
        return (
            Selection.objects.filter(
                market__status=Market.Status.OPEN,
                market__match__kickoff__gt=now,
                picks__bet__created_at__gte=now - timedelta(days=7),
            )
            .select_related("market__match__competition")
            .prefetch_related(Prefetch("market__match__home", queryset=TEAMS), Prefetch("market__match__away", queryset=TEAMS))
            .annotate(bet_count=Count("picks"))
            .order_by("-bet_count", "id")
        )


# ---------------------------------------------------------------- predictions (free, no LC)


def competition_of(request):
    """The active league of ?competition=PL, or None (an unknown value gives an empty answer)."""
    return Competition.objects.filter(is_active=True, code=request.query_params.get("competition")).first()


def matchday_of(request, competition):
    """?matchday=11, else the league's current matchday (None when there is none)."""
    value = request.query_params.get("matchday")
    if value is None:
        season = Season.objects.filter(competition=competition, is_current=True).first()
        return season.current_matchday if season else None
    return int(value) if value.isdigit() else None


def prediction_state(match, prediction, now):
    if predictions.is_open(match, now):
        return "open"
    if prediction is not None and prediction.outcome != Prediction.Outcome.PENDING:
        return "scored"
    return "locked"


def save_one(user, match, home, away):
    (prediction, created), = predictions.save_predictions(user, [(match, home, away)])
    return prediction, created


class PredictionViewSet(viewsets.ViewSet):
    """GET ?competition=PL&matchday=11: that matchday's matches with my prediction on each.
    POST {match, home_goals, away_goals} and PUT /<match> save one; POST /bulk {predictions: [...]} saves
    several at once (all or nothing). Until kickoff only."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        competition = competition_of(request)
        matchday = matchday_of(request, competition) if competition else None
        if competition is None or matchday is None:
            return Response([])
        matches = BET_MATCHES.filter(competition=competition, season__is_current=True, matchday=matchday).order_by(
            "kickoff", "id"
        )
        mine = {row.match_id: row for row in Prediction.objects.filter(user=request.user, match__in=matches)}
        now = timezone.now()
        context = {"lang": get_lang(request), "request": request}
        return Response(
            [
                {
                    "match": MatchSerializer(match, context=context).data,
                    "prediction": PredictionSerializer(mine[match.id]).data if match.id in mine else None,
                    "state": prediction_state(match, mine.get(match.id), now),
                }
                for match in matches
            ]
        )

    def create(self, request):
        serializer = PredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prediction, created = save_one(request.user, data["match"], data["home_goals"], data["away_goals"])
        return Response(
            PredictionSerializer(prediction).data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK
        )

    def update(self, request, pk=None):
        serializer = PredictionRequestSerializer(data={**request.data, "match": pk})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        prediction, _ = save_one(request.user, data["match"], data["home_goals"], data["away_goals"])
        return Response(PredictionSerializer(prediction).data)

    @action(detail=False, methods=["post"])
    def bulk(self, request):
        serializer = BulkPredictionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        rows = serializer.validated_data["predictions"]
        saved = predictions.save_predictions(
            request.user, [(row["match"], row["home_goals"], row["away_goals"]) for row in rows]
        )
        return Response([PredictionSerializer(prediction).data for prediction, _ in saved])


class PredictionLeaderboardViewSet(viewsets.ViewSet):
    """?competition=PL, optional ?matchday=11 (without it: the season). The top 6, my row and my rank."""

    permission_classes = [AllowAny]

    def list(self, request):
        empty = {"players": 0, "rows": [], "me": None}
        competition = competition_of(request)
        if competition is None:
            return Response(empty)
        matchday = None
        if "matchday" in request.query_params:
            matchday = matchday_of(request, competition)
            if matchday is None:
                return Response(empty)
        user = request.user if request.user.is_authenticated else None
        return Response(predictions.leaderboard(competition, matchday, user))


class PredictionStatsViewSet(viewsets.ViewSet):
    """?competition=PL: my points, rank, exact scores and right-result share this season."""

    permission_classes = [IsAuthenticated]

    def list(self, request):
        competition = competition_of(request)
        if competition is None:
            return Response({"points": 0, "rank": None, "exact": 0, "right_percent": 0, "played": 0, "players": 0})
        return Response(predictions.my_stats(request.user, competition))


class MatchdayViewSet(viewsets.ViewSet):
    """?competition=PL: the current season's matchdays with how many matches are open and finished."""

    permission_classes = [AllowAny]

    def list(self, request):
        competition = competition_of(request)
        season = Season.objects.filter(competition=competition, is_current=True).first() if competition else None
        if season is None:
            return Response([])
        now = timezone.now()
        rows = {}
        for match in Match.objects.filter(season=season, matchday__isnull=False):
            row = rows.setdefault(match.matchday, {"matchday": match.matchday, "matches": 0, "open": 0, "finished": 0})
            row["matches"] += 1
            row["open"] += predictions.is_open(match, now)
            row["finished"] += match.status == Match.Status.FINISHED
        return Response([{**rows[day], "current": day == season.current_matchday} for day in sorted(rows)])


class StandingZoneViewSet(FootballViewSet):
    """?competition=PL: the coloured bands of the table (set per league in the admin)."""

    queryset = StandingZone.objects.filter(competition__is_active=True)
    serializer_class = StandingZoneSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        code = self.request.query_params.get("competition")
        return qs.filter(competition__code=code) if code else qs


class PredictionLabelViewSet(LangFilteredViewSet):
    queryset = PredictionLabel.objects.all()
    serializer_class = PredictionLabelSerializer


# ---------------------------------------------------------------- live scores (display only)


class LiveMatchViewSet(FootballViewSet):
    """The matches in play now with their live score. Display only: nothing here settles a bet."""

    queryset = LiveScore.objects.select_related("match__competition").prefetch_related(
        Prefetch("match__home", queryset=TEAMS), Prefetch("match__away", queryset=TEAMS)
    )
    serializer_class = LiveScoreSerializer


class LiveLabelViewSet(LangFilteredViewSet):
    queryset = LiveLabel.objects.all()
    serializer_class = LiveLabelSerializer
