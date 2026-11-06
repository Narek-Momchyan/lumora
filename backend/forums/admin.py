from django.contrib import admin, messages

from wallet.admin import ReadOnlyAdmin
from . import services
from .models import BannedWord, Forum, ForumBan, ForumLabel, Post, PostReport, Rule, Topic


@admin.register(Forum)
class ForumAdmin(ReadOnlyAdmin):
    """Forums are created by the football sync, one per club."""

    list_display = ["team", "created_at"]
    search_fields = ["team__name"]


@admin.register(Topic)
class TopicAdmin(admin.ModelAdmin):
    """Moderators pin and lock topics; nothing else about a topic is edited by hand."""

    list_display = ["title", "forum", "tag", "author", "is_pinned", "is_locked", "post_count", "last_post_at"]
    list_filter = ["tag", "is_pinned", "is_locked"]
    search_fields = ["title", "forum__team__name", "author__display_name"]
    fields = ["forum", "author", "title", "tag", "match", "post_count", "created_at", "is_pinned", "is_locked"]
    readonly_fields = ["forum", "author", "title", "tag", "match", "post_count", "created_at"]
    actions = ["pin", "unpin", "lock", "unlock"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Pin the selected topics")
    def pin(self, request, queryset):
        queryset.update(is_pinned=True)

    @admin.action(description="Unpin the selected topics")
    def unpin(self, request, queryset):
        queryset.update(is_pinned=False)

    @admin.action(description="Lock the selected topics (no new posts)")
    def lock(self, request, queryset):
        queryset.update(is_locked=True)

    @admin.action(description="Unlock the selected topics")
    def unlock(self, request, queryset):
        queryset.update(is_locked=False)


def hide_action(rule):
    @admin.action(description=f"Hide the selected posts: {Rule(rule).label}")
    def action(modeladmin, request, queryset):
        for post in queryset:
            services.hide_post(post, rule, request.user)
        messages.success(request, f"{queryset.count()} post(s) hidden.")

    action.__name__ = f"hide_{rule}"
    return action


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    """Moderators read posts and hide or unhide them. A hidden post's text is never sent to anyone."""

    list_display = ["id", "topic", "author", "short_body", "is_hidden", "hidden_rule", "created_at"]
    list_filter = ["is_hidden", "hidden_rule"]
    search_fields = ["body", "author__display_name", "topic__title"]
    fields = ["topic", "author", "body", "prediction", "created_at", "hidden_by", "hidden_at"]
    readonly_fields = fields
    actions = [hide_action(rule) for rule in Rule.values] + ["unhide", "ban_author"]

    @admin.display(description="Text")
    def short_body(self, obj):
        return obj.body[:80]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Unhide the selected posts")
    def unhide(self, request, queryset):
        for post in queryset:
            services.unhide_post(post)

    @admin.action(description=f"Ban the authors of the selected posts for {services.BAN_DAYS} days")
    def ban_author(self, request, queryset):
        for user in {post.author for post in queryset}:
            services.ban_player(user, request.user, reason="Banned from a post in the admin")
        messages.success(request, "Authors banned.")


@admin.register(PostReport)
class PostReportAdmin(admin.ModelAdmin):
    list_display = ["id", "post", "reporter", "reason", "status", "created_at"]
    list_filter = ["status", "reason"]
    search_fields = ["post__body", "reporter__display_name"]
    fields = ["post", "reporter", "reason", "status", "created_at"]
    readonly_fields = ["post", "reporter", "reason", "created_at"]
    actions = ["hide_post", "dismiss"]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.action(description="Hide the reported posts (the report's rule) and close their reports")
    def hide_post(self, request, queryset):
        for report in queryset.select_related("post"):
            services.hide_post(report.post, report.reason, request.user)

    @admin.action(description="Dismiss the selected reports")
    def dismiss(self, request, queryset):
        for report in queryset.select_related("post"):
            services.dismiss_reports(report.post)


@admin.register(ForumBan)
class ForumBanAdmin(admin.ModelAdmin):
    """Ban a player from posting until a date: add one here, or use the action on a post."""

    list_display = ["user", "until", "reason", "created_by", "created_at"]
    search_fields = ["user__email", "user__display_name"]
    autocomplete_fields = ["user"]

    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(BannedWord)
class BannedWordAdmin(admin.ModelAdmin):
    list_display = ["word", "lang", "inside_words"]
    list_filter = ["lang", "inside_words"]
    search_fields = ["word"]


@admin.register(ForumLabel)
class ForumLabelAdmin(admin.ModelAdmin):
    list_display = ["lang", "new_topic", "post_reply", "hidden_by_moderator"]
    list_filter = ["lang"]
