from django.db.models import Q
from rest_framework import serializers

from base.serializers import ModelSerializer
from .betting import MAX_PICKS
from .models import (
    Bet,
    BetLabel,
    BetSelection,
    Competition,
    LiveLabel,
    LiveScore,
    Market,
    Match,
    Prediction,
    PredictionLabel,
    Selection,
    SportsPageLabel,
    SportsUiLabel,
    Standing,
    StandingZone,
    Team,
)


class SportsPageLabelSerializer(ModelSerializer):
    class Meta:
        model = SportsPageLabel
        fields = "__all__"


def translated(obj, lang, field):
    """The value in the request's language (set in the admin), else the provider's English one."""
    for name in obj.names.all():  # prefetched by the views
        if name.lang == lang and getattr(name, field):
            return getattr(name, field)
    return getattr(obj, field)


class TeamSerializer(ModelSerializer):
    name = serializers.SerializerMethodField()
    short_name = serializers.SerializerMethodField()

    class Meta:
        model = Team
        fields = ["id", "name", "short_name", "tla", "color", "text_color", "crest"]

    def get_name(self, obj):
        return translated(obj, self.context["lang"], "name")

    def get_short_name(self, obj):
        return translated(obj, self.context["lang"], "short_name")


class CompetitionSerializer(ModelSerializer):
    name = serializers.SerializerMethodField()
    season = serializers.SerializerMethodField()

    class Meta:
        model = Competition
        fields = ["id", "code", "name", "flag", "order", "season"]

    def get_name(self, obj):
        return translated(obj, self.context["lang"], "name")

    def get_season(self, obj):
        season = next((row for row in obj.seasons.all() if row.is_current), None)
        if season is None:
            return None
        return {
            "start_date": season.start_date,
            "end_date": season.end_date,
            "current_matchday": season.current_matchday,
        }


class MatchSerializer(ModelSerializer):
    competition = serializers.CharField(source="competition.code")
    home = TeamSerializer()
    away = TeamSerializer()
    market_count = serializers.IntegerField(read_only=True, default=0)  # "+N markets"; 0 where not annotated

    class Meta:
        model = Match
        fields = [
            "id",
            "competition",
            "matchday",
            "stage",
            "group",
            "home",
            "away",
            "kickoff",
            "status",
            "duration",
            "home_score",
            "away_score",
            "home_half",
            "away_half",
            "home_regular",
            "away_regular",
            "home_extra",
            "away_extra",
            "home_penalties",
            "away_penalties",
            "market_count",
        ]


class StandingSerializer(ModelSerializer):
    team = TeamSerializer()

    class Meta:
        model = Standing
        fields = [
            "id",
            "stage",
            "group",
            "position",
            "team",
            "played",
            "won",
            "draw",
            "lost",
            "goals_for",
            "goals_against",
            "goal_difference",
            "points",
            "form",
        ]


class BetLabelSerializer(ModelSerializer):
    class Meta:
        model = BetLabel
        fields = "__all__"


class SelectionSerializer(ModelSerializer):
    class Meta:
        model = Selection
        fields = ["id", "code", "odds", "previous_odds", "probability", "result"]


class MarketSerializer(ModelSerializer):
    selections = SelectionSerializer(many=True)

    class Meta:
        model = Market
        fields = ["id", "match", "kind", "line", "status", "selections"]


class BetSelectionSerializer(ModelSerializer):
    market = serializers.CharField(source="selection.market.kind")
    line = serializers.DecimalField(source="selection.market.line", max_digits=4, decimal_places=1, allow_null=True)
    code = serializers.CharField(source="selection.code")
    match = MatchSerializer()

    class Meta:
        model = BetSelection
        fields = ["id", "selection", "market", "line", "code", "odds", "result", "match"]


class BetSerializer(ModelSerializer):
    picks = BetSelectionSerializer(many=True)

    class Meta:
        model = Bet
        fields = [
            "id",
            "key",
            "kind",
            "stake",
            "total_odds",
            "potential_win",
            "status",
            "payout",
            "created_at",
            "settled_at",
            "picks",
        ]


class PickRequestSerializer(serializers.Serializer):
    selection = serializers.IntegerField()
    odds = serializers.DecimalField(max_digits=7, decimal_places=2)


class BetRequestSerializer(serializers.Serializer):
    key = serializers.CharField(max_length=40)
    stake = serializers.DecimalField(max_digits=12, decimal_places=2)
    selections = PickRequestSerializer(many=True, allow_empty=False, max_length=MAX_PICKS)


class SportsUiLabelSerializer(ModelSerializer):
    class Meta:
        model = SportsUiLabel
        fields = "__all__"


def form_of(team_id, before, limit=5):
    """W / D / L of the team's last matches before `before`, newest first (regular-time score)."""
    rows = (
        Match.objects.filter(status=Match.Status.FINISHED, kickoff__lt=before)
        .filter(Q(home_id=team_id) | Q(away_id=team_id))
        .order_by("-kickoff")[:limit]
    )
    form = []
    for match in rows:
        home = match.home_regular if match.home_regular is not None else match.home_score
        away = match.away_regular if match.away_regular is not None else match.away_score
        if home is None or away is None:
            continue
        goals, against = (home, away) if match.home_id == team_id else (away, home)
        form.append("W" if goals > against else "L" if goals < against else "D")
    return form


def table_row(team_id, season_id):
    row = Standing.objects.filter(season_id=season_id, team_id=team_id, type="TOTAL").order_by("stage", "group").first()
    return {"position": row.position, "points": row.points} if row else None


class MatchDetailSerializer(MatchSerializer):
    """One match page: the match, both teams' recent form and their place in the table."""

    home_form = serializers.SerializerMethodField()
    away_form = serializers.SerializerMethodField()
    home_table = serializers.SerializerMethodField()
    away_table = serializers.SerializerMethodField()

    class Meta(MatchSerializer.Meta):
        fields = [*MatchSerializer.Meta.fields, "home_form", "away_form", "home_table", "away_table"]

    def get_home_form(self, obj):
        return form_of(obj.home_id, obj.kickoff)

    def get_away_form(self, obj):
        return form_of(obj.away_id, obj.kickoff)

    def get_home_table(self, obj):
        return table_row(obj.home_id, obj.season_id)

    def get_away_table(self, obj):
        return table_row(obj.away_id, obj.season_id)


class PopularPickSerializer(ModelSerializer):
    market = serializers.CharField(source="market.kind")
    line = serializers.DecimalField(source="market.line", max_digits=4, decimal_places=1, allow_null=True)
    match = MatchSerializer(source="market.match")
    picks = serializers.IntegerField(source="bet_count")

    class Meta:
        model = Selection
        fields = ["id", "market", "line", "code", "odds", "previous_odds", "match", "picks"]


class PredictionLabelSerializer(ModelSerializer):
    class Meta:
        model = PredictionLabel
        fields = "__all__"


class StandingZoneSerializer(ModelSerializer):
    class Meta:
        model = StandingZone
        fields = ["id", "kind", "from_position", "to_position"]


class PredictionSerializer(ModelSerializer):
    class Meta:
        model = Prediction
        fields = ["id", "match", "home_goals", "away_goals", "outcome", "points", "updated_at"]


class PredictionRequestSerializer(serializers.Serializer):
    """Whole numbers only; the 0-20 range and the kickoff lock are checked by sports.predictions."""

    match = serializers.IntegerField()
    home_goals = serializers.IntegerField()
    away_goals = serializers.IntegerField()


class BulkPredictionRequestSerializer(serializers.Serializer):
    predictions = PredictionRequestSerializer(many=True, allow_empty=False, max_length=50)


class LiveLabelSerializer(ModelSerializer):
    class Meta:
        model = LiveLabel
        fields = "__all__"


class LiveScoreSerializer(ModelSerializer):
    """A match in play with its live row; `delayed` is true when the score is football-data's."""

    match = MatchSerializer()
    delayed = serializers.SerializerMethodField()

    class Meta:
        model = LiveScore
        fields = ["id", "match", "status", "minute", "home_score", "away_score", "source", "delayed", "goal_at", "updated_at"]

    def get_delayed(self, obj):
        return obj.source == LiveScore.Source.FOOTBALL_DATA
