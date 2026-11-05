from django.contrib import admin
from django.utils.html import format_html

from wallet.admin import ReadOnlyAdmin
from .models import (
    Bet,
    BetLabel,
    BetSelection,
    Competition,
    CompetitionName,
    Market,
    Match,
    ModelRun,
    Season,
    Selection,
    SportsPageLabel,
    Standing,
    SyncRun,
    Team,
    TeamAlias,
    TeamName,
)


def preview(file):
    if not file:
        return "-"
    return format_html('<img src="{}" style="height: 32px; width: 32px; object-fit: contain;">', file.url)


@admin.register(SportsPageLabel)
class SportsPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "page_title", "hero_title"]
    list_filter = ["lang"]


class CompetitionNameInline(admin.TabularInline):
    model = CompetitionName
    extra = 0


@admin.register(Competition)
class CompetitionAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "flag_preview", "order", "is_active"]
    list_filter = ["is_active"]
    search_fields = ["name", "code"]
    readonly_fields = ["flag_preview", "provider_id"]
    inlines = [CompetitionNameInline]

    @admin.display(description="Flag")
    def flag_preview(self, obj):
        return preview(obj.flag)


class TeamNameInline(admin.TabularInline):
    model = TeamName
    extra = 0


class TeamAliasInline(admin.TabularInline):
    model = TeamAlias
    extra = 0


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    """Names come from the provider; colours, the crest and translations are edited here."""

    list_display = ["name", "tla", "crest_preview", "color", "text_color", "crest_locked"]
    list_filter = ["competitions", "crest_locked"]
    search_fields = ["name", "short_name", "tla", "aliases__name"]
    readonly_fields = ["crest_preview", "provider_id", "crest_source_url"]
    filter_horizontal = ["competitions"]
    inlines = [TeamNameInline, TeamAliasInline]

    @admin.display(description="Crest")
    def crest_preview(self, obj):
        return preview(obj.crest)

    def save_model(self, request, obj, form, change):
        # A crest uploaded by hand stays: the next sync must not put the provider's back.
        if "crest" in form.changed_data:
            obj.crest_locked = True
        super().save_model(request, obj, form, change)


@admin.register(Season)
class SeasonAdmin(ReadOnlyAdmin):
    list_display = ["competition", "start_date", "end_date", "current_matchday", "is_current"]
    list_filter = ["competition", "is_current"]


@admin.register(Match)
class MatchAdmin(ReadOnlyAdmin):
    list_display = ["kickoff", "competition", "home", "away", "status", "home_score", "away_score", "duration"]
    list_filter = ["competition", "status", "duration"]
    search_fields = ["home__name", "away__name"]
    date_hierarchy = "kickoff"


@admin.register(Standing)
class StandingAdmin(ReadOnlyAdmin):
    list_display = ["season", "group", "position", "team", "played", "points", "goal_difference", "form"]
    list_filter = ["season__competition"]


@admin.register(SyncRun)
class SyncRunAdmin(ReadOnlyAdmin):
    list_display = ["started_at", "kind", "competition", "requests", "created", "updated", "ok"]
    list_filter = ["kind", "ok", "competition"]


@admin.register(BetLabel)
class BetLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "match_result", "total_goals", "correct_score"]
    list_filter = ["lang"]


@admin.register(ModelRun)
class ModelRunAdmin(ReadOnlyAdmin):
    list_display = ["fitted_at", "matches_used", "priced_matches", "rho"]


class SelectionInline(admin.TabularInline):
    model = Selection
    extra = 0
    can_delete = False
    readonly_fields = ["code", "odds", "previous_odds", "probability", "result"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Market)
class MarketAdmin(ReadOnlyAdmin):
    list_display = ["match", "kind", "line", "status", "updated_at"]
    list_filter = ["kind", "status", "match__competition"]
    search_fields = ["match__home__name", "match__away__name"]
    inlines = [SelectionInline]


class BetSelectionInline(admin.TabularInline):
    model = BetSelection
    extra = 0
    can_delete = False
    readonly_fields = ["selection", "match", "odds", "result"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Bet)
class BetAdmin(ReadOnlyAdmin):
    """Bets and their money are never edited by hand (Rule 9)."""

    list_display = ["created_at", "user", "kind", "stake", "total_odds", "status", "payout"]
    list_filter = ["kind", "status"]
    search_fields = ["user__email", "key"]
    inlines = [BetSelectionInline]
