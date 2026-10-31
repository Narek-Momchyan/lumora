from django.contrib import admin
from django.utils.html import format_html


class ImagePreviewMixin:
    """Shows a small preview of the uploaded `image` next to the upload field."""

    readonly_fields = ["image_preview"]

    @admin.display(description="Preview")
    def image_preview(self, obj):
        if obj is None or not obj.image:
            return "-"
        return format_html('<img src="{}" style="max-height: 80px; max-width: 160px;">', obj.image.url)
