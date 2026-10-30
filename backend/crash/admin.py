from django.contrib import admin

from .models import CrashBet


@admin.register(CrashBet)
class CrashBetAdmin(admin.ModelAdmin):
    list_display = ["user", "amount", "target", "crash_point", "payout", "created_at"]
    search_fields = ["user__email", "server_seed_hash"]

    # Settled rounds are history: they are never added or edited by hand.
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
