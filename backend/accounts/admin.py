from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import LoginPageLabel, User


@admin.register(User)
class PlayerAdmin(UserAdmin):
    list_display = ["email", "display_name", "is_staff", "date_joined"]
    search_fields = ["email", "display_name"]
    fieldsets = UserAdmin.fieldsets + (("Lumora", {"fields": ["display_name"]}),)


@admin.register(LoginPageLabel)
class LoginPageLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "login_title", "signup_title"]
    list_filter = ["lang"]
