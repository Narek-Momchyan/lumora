from rest_framework import serializers

from base.serializers import ModelSerializer
from .betting import MAX_PICKS
from .models import (
    Bet,
    BetLabel,
    BetSelection,
    Competition,
    Market,
    Match,
    Selection,
    SportsPageLabel,
    Standing,
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
