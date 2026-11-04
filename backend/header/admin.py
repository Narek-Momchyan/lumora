from django.contrib import admin

from base.admin import ImagePreviewMixin
from .models import HeaderLabel, Language, Logo, SidebarItem


@admin.register(Logo)
class LogoAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ["name", "image_preview"]

    def has_add_permission(self, request):
        return not Logo.objects.exists()  # the site has one logo


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "order"]
    list_filter = ["code"]


@admin.register(SidebarItem)
class SidebarItemAdmin(admin.ModelAdmin):
    list_display = ["title", "url", "category", "lang", "order", "is_soon"]
    list_filter = ["lang", "category", "is_soon"]


@admin.register(HeaderLabel)
class HeaderLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "search_placeholder", "demo_badge", "logout_button"]
    list_filter = ["lang"]
