from django.contrib import admin

from .models import SeedPair


@admin.register(SeedPair)
class SeedPairAdmin(admin.ModelAdmin):
    list_display = ["user", "server_seed_hash", "client_seed", "nonce", "is_active", "revealed_at"]
    list_filter = ["is_active"]
    search_fields = ["user__email", "server_seed_hash"]
    exclude = ["server_seed"]  # never show an active secret, even to staff
    readonly_fields = ["server_seed_hash"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
