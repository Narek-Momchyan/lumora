from django.contrib import admin

from .models import SportsPageLabel


@admin.register(SportsPageLabel)
class SportsPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "page_title", "hero_title"]
    list_filter = ["lang"]
