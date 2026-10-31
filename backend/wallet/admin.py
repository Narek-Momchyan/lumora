from django.contrib import admin

from .models import JackpotPool, Transaction, Wallet


class ReadOnlyAdmin(admin.ModelAdmin):
    """Money is changed only by wallet.services, never by hand in the admin."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(ReadOnlyAdmin):
    list_display = ["user", "balance", "last_bonus_at", "updated_at"]
    search_fields = ["user__email"]


@admin.register(Transaction)
class TransactionAdmin(ReadOnlyAdmin):
    list_display = ["wallet", "kind", "amount", "balance_after", "game", "round_id", "created_at"]
    list_filter = ["kind", "game"]
    search_fields = ["wallet__user__email", "round_id"]


@admin.register(JackpotPool)
class JackpotPoolAdmin(ReadOnlyAdmin):
    list_display = ["tier", "amount", "updated_at"]
