from django.contrib import admin

from .models import Game


@admin.register(Game)
class GameAdmin(admin.ModelAdmin):
    list_display = ["title", "slug", "category", "rtp", "is_active", "is_featured", "sort_order"]
    list_editable = ["is_active", "is_featured", "sort_order"]
    list_filter = ["category", "is_active"]
    prepopulated_fields = {"slug": ["title"]}
