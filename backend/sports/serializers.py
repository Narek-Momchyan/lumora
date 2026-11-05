from rest_framework import serializers

from base.serializers import ModelSerializer
from .models import Competition, Match, SportsPageLabel, Standing, Team


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
