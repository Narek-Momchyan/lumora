from django.contrib import admin

from wallet.admin import ReadOnlyAdmin
from .models import RouletteBotSettings, RouletteChain, RouletteLine, RoulettePageLabel, RouletteRound, RouletteSlip


@admin.register(RouletteChain)
class RouletteChainAdmin(ReadOnlyAdmin):
    list_display = ["id", "commitment", "length", "created_at"]
    exclude = ["last_seed"]  # every future seed comes from it, never show it, even to staff


@admin.register(RouletteRound)
class RouletteRoundAdmin(ReadOnlyAdmin):
    list_display = ["number", "status", "revealed_result", "spin_started_at", "settled_at"]
    list_filter = ["status"]
    search_fields = ["number", "seed_hash"]

    @admin.display(description="Result")
    def revealed_result(self, obj):
        return "-" if obj.status == RouletteRound.Status.BETTING else obj.result

    def get_exclude(self, request, obj=None):
        # A live round's secrets stay secret, even from staff.
        if obj and obj.status == RouletteRound.Status.SETTLED:
            return []
        if obj and obj.status == RouletteRound.Status.SPINNING:
            return ["seed"]
        return ["seed", "result"]


class RouletteLineInline(admin.TabularInline):
    model = RouletteLine
    extra = 0

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(RouletteSlip)
class RouletteSlipAdmin(ReadOnlyAdmin):
    list_display = ["user", "round", "amount", "payout", "created_at"]
    search_fields = ["user__email"]
    inlines = [RouletteLineInline]


@admin.register(RouletteBotSettings)
class RouletteBotSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "is_enabled", "count", "min_bet", "max_bet"]

    def changelist_view(self, request, extra_context=None):
        RouletteBotSettings.load()  # the one row is always there to open
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(RoulettePageLabel)
class RoulettePageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "page_title", "place_bets"]
    list_filter = ["lang"]
