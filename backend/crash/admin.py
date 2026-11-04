from django.contrib import admin

from wallet.admin import ReadOnlyAdmin
from .models import CrashBotSettings, CrashChain, CrashPageLabel, CrashRound, RoundBet


@admin.register(CrashChain)
class CrashChainAdmin(ReadOnlyAdmin):
    list_display = ["id", "commitment", "length", "created_at"]
    exclude = ["last_seed"]  # every future seed comes from it, never show it, even to staff


@admin.register(CrashRound)
class CrashRoundAdmin(ReadOnlyAdmin):
    list_display = ["number", "status", "revealed_crash_point", "started_at", "crashed_at"]
    list_filter = ["status"]
    search_fields = ["number", "seed_hash"]

    @admin.display(description="Crash point")
    def revealed_crash_point(self, obj):
        return obj.crash_point if obj.status == CrashRound.Status.CRASHED else "-"

    def get_exclude(self, request, obj=None):
        # A live round's result stays secret, even from staff.
        return [] if obj and obj.status == CrashRound.Status.CRASHED else ["seed", "crash_point"]


@admin.register(RoundBet)
class RoundBetAdmin(ReadOnlyAdmin):
    list_display = ["user", "round", "amount", "target", "status", "multiplier", "payout", "created_at"]
    list_filter = ["status"]
    search_fields = ["user__email"]


@admin.register(CrashBotSettings)
class CrashBotSettingsAdmin(admin.ModelAdmin):
    list_display = ["__str__", "is_enabled", "count", "min_bet", "max_bet"]

    def changelist_view(self, request, extra_context=None):
        CrashBotSettings.load()  # the one row is always there to open
        return super().changelist_view(request, extra_context)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(CrashPageLabel)
class CrashPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "page_title", "cash_out"]
    list_filter = ["lang"]
