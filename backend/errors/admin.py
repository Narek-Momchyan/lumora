from django.contrib import admin

from .models import ErrorMessage


@admin.register(ErrorMessage)
class ErrorMessageAdmin(admin.ModelAdmin):
    list_display = ["code", "lang", "text"]
    list_filter = ["lang"]
    search_fields = ["code", "text"]
