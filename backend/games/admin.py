from django.contrib import admin

from base.admin import ImagePreviewMixin
from .models import Game, GameCategory, LobbyPageLabel


@admin.register(Game)
class GameAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ["title", "slug", "category", "rtp", "is_active", "is_playable", "is_featured", "sort_order"]
    list_editable = ["is_active", "is_playable", "is_featured", "sort_order"]
    list_filter = ["category", "is_active", "is_playable"]
    prepopulated_fields = {"slug": ["title"]}


@admin.register(GameCategory)
class GameCategoryAdmin(admin.ModelAdmin):
    list_display = ["filter_label", "card_label", "code", "lang", "order", "is_soon"]
    list_filter = ["lang", "code"]


@admin.register(LobbyPageLabel)
class LobbyPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "bonus_title", "section_popular"]
    list_filter = ["lang"]
