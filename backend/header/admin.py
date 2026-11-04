from django.contrib import admin
from django.utils.html import format_html

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
    list_display = ["title", "mode", "group", "url", "icon_preview", "lang", "order", "is_soon"]
    list_filter = ["mode", "lang", "group", "is_soon"]
    readonly_fields = ["icon_preview"]

    @admin.display(description="Icon")
    def icon_preview(self, obj):
        if obj is None or not obj.icon:
            return "-"
        return format_html('<img src="{}" style="height: 20px; width: 20px;">', obj.icon.url)


@admin.register(HeaderLabel)
class HeaderLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "search_placeholder", "demo_badge", "logout_button"]
    list_filter = ["lang"]
