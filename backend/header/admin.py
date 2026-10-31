from django.contrib import admin

from base.admin import ImagePreviewMixin
from .models import Language, Logo


@admin.register(Logo)
class LogoAdmin(ImagePreviewMixin, admin.ModelAdmin):
    list_display = ["name", "image_preview"]

    def has_add_permission(self, request):
        return not Logo.objects.exists()  # the site has one logo


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "order"]
    list_filter = ["code"]
