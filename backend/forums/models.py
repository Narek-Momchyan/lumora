from django.conf import settings
from django.db import models
from django.utils import timezone

from base.constants import LANG_CHOICES


class Rule(models.TextChoices):
    """The forum rules a report can name and a moderator can hide a post for."""

    INSULT_HATE = "insult_hate", "Insult or hate"
    SPAM_ADS = "spam_ads", "Spam or ads"
    REAL_MONEY = "real_money", "Real-money betting talk"
    OTHER = "other", "Something else"


class Forum(models.Model):
    """One forum per club of our competitions, created by the football sync (forums.services.ensure_forums)."""

    team = models.OneToOneField("sports.Team", related_name="forum", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Forums"
        ordering = ["team__name"]

    def __str__(self):
        return f"{self.team} fans"


class Topic(models.Model):
    class Tag(models.TextChoices):
        MATCH_TALK = "match_talk", "Match talk"
        TRANSFERS = "transfers", "Transfers"
        TACTICS = "tactics", "Tactics"
        PREDICTIONS = "predictions", "Predictions"
        OFF_TOPIC = "off_topic", "Off-topic"

    forum = models.ForeignKey(Forum, related_name="topics", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="forum_topics", on_delete=models.CASCADE)
    title = models.CharField(max_length=120)
    tag = models.CharField(max_length=20, choices=Tag.choices)
    match = models.ForeignKey("sports.Match", null=True, blank=True, related_name="topics", on_delete=models.SET_NULL)
    is_pinned = models.BooleanField(default=False)
    is_locked = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)  # set by the service, so tests can pass the time
    last_post_at = models.DateTimeField(db_index=True)
    post_count = models.PositiveIntegerField(default=0, help_text="Posts including the opening one")

    class Meta:
        verbose_name_plural = "Topics"
        ordering = ["-is_pinned", "-last_post_at", "-id"]

    def __str__(self):
        return self.title


class Post(models.Model):
    topic = models.ForeignKey(Topic, related_name="posts", on_delete=models.CASCADE)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="forum_posts", on_delete=models.CASCADE)
    body = models.TextField(help_text="Plain text, shown as text only")
    prediction = models.ForeignKey(
        "sports.Prediction", null=True, blank=True, related_name="forum_posts", on_delete=models.SET_NULL
    )
    is_hidden = models.BooleanField(default=False, help_text="On: the text is not sent to anyone")
    hidden_rule = models.CharField(max_length=12, choices=Rule.choices, blank=True)
    hidden_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL, editable=False
    )
    hidden_at = models.DateTimeField(null=True, blank=True, editable=False)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)

    class Meta:
        verbose_name_plural = "Posts"
        ordering = ["id"]

    def __str__(self):
        return f"Post {self.pk} in {self.topic_id}"


class PostLike(models.Model):
    post = models.ForeignKey(Post, related_name="likes", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="forum_likes", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Post likes"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["post", "user"], name="unique_post_like_post_user")]


class TopicView(models.Model):
    """A player who opened a topic: the view count is distinct players, so reloading cannot inflate it."""

    topic = models.ForeignKey(Topic, related_name="viewers", on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="+", on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = "Topic views"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["topic", "user"], name="unique_topic_view_topic_user")]


class PostReport(models.Model):
    class Status(models.TextChoices):
        OPEN = "open", "Open"
        DISMISSED = "dismissed", "Dismissed"
        ACTIONED = "actioned", "Post hidden"

    post = models.ForeignKey(Post, related_name="reports", on_delete=models.CASCADE)
    reporter = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="forum_reports", on_delete=models.CASCADE)
    reason = models.CharField(max_length=12, choices=Rule.choices)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Post reports"
        ordering = ["-created_at", "-id"]
        constraints = [models.UniqueConstraint(fields=["post", "reporter"], name="unique_post_report_post_reporter")]


class ForumBan(models.Model):
    """A player who may not post, like or report until `until`."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, related_name="forum_bans", on_delete=models.CASCADE)
    until = models.DateTimeField()
    reason = models.CharField(max_length=200, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, related_name="+", on_delete=models.SET_NULL, editable=False
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Forum bans"
        ordering = ["-until", "-id"]

    def __str__(self):
        return f"{self.user} until {self.until:%Y-%m-%d %H:%M}"


class BannedWord(models.Model):
    """A word the forum refuses, per language. `key` is the word as the matcher sees it (forums/text.py)."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES)
    word = models.CharField(max_length=60, help_text="A word or a short phrase")
    key = models.CharField(max_length=60, editable=False)
    inside_words = models.BooleanField(
        default=False,
        help_text="Also refuse it inside longer words. For stems of heavily inflected languages (Armenian, Russian)",
    )

    class Meta:
        verbose_name_plural = "Banned words"
        ordering = ["lang", "word"]
        constraints = [models.UniqueConstraint(fields=["lang", "key"], name="unique_banned_word_lang_key")]

    def save(self, *args, **kwargs):
        from . import text

        self.key = text.key_of(self.word)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.word} ({self.lang})"


class ForumLabel(models.Model):
    """Every text of the forum pages in one language."""

    lang = models.CharField(max_length=10, choices=LANG_CHOICES, db_index=True)
    page_text = models.CharField(max_length=255)
    clubs_title = models.CharField(max_length=120)
    topics_count = models.CharField(max_length=120, help_text="{count} is replaced")
    posts_count = models.CharField(max_length=120, help_text="{count} is replaced")
    fans = models.CharField(max_length=120, help_text="{club} is replaced: Arsenal fans")
    all_topics = models.CharField(max_length=120)
    tag_match_talk = models.CharField(max_length=60)
    tag_transfers = models.CharField(max_length=60)
    tag_tactics = models.CharField(max_length=60)
    tag_predictions = models.CharField(max_length=60)
    tag_off_topic = models.CharField(max_length=60)
    sort_latest = models.CharField(max_length=60)
    sort_replies = models.CharField(max_length=60)
    sort_views = models.CharField(max_length=60)
    pinned = models.CharField(max_length=60)
    locked = models.CharField(max_length=60)
    replies = models.CharField(max_length=60)
    views = models.CharField(max_length=60)
    by_author = models.CharField(max_length=120, help_text="{name} is replaced")
    new_topic = models.CharField(max_length=120)
    topic_title = models.CharField(max_length=120)
    topic_body = models.CharField(max_length=120)
    topic_tag = models.CharField(max_length=120)
    create_topic = models.CharField(max_length=120)
    cancel = models.CharField(max_length=60)
    no_topics = models.CharField(max_length=160)
    no_clubs = models.CharField(max_length=160, help_text="Shown when a league has no forums yet")
    next_match = models.CharField(max_length=120)
    open_match = models.CharField(max_length=160)
    rules_title = models.CharField(max_length=120)
    rule_respect = models.CharField(max_length=200)
    rule_on_topic = models.CharField(max_length=200)
    rule_no_betting = models.CharField(max_length=200)
    rule_no_personal = models.CharField(max_length=200)
    rules_note = models.CharField(max_length=400)
    breadcrumb_forums = models.CharField(max_length=120)
    author_tag = models.CharField(max_length=60)
    top_predictor = models.CharField(max_length=60)
    anonymous_player = models.CharField(max_length=120, help_text="Shown for an author without a display name")
    reply = models.CharField(max_length=60)
    report = models.CharField(max_length=60)
    like = models.CharField(max_length=60)
    hidden_by_moderator = models.CharField(max_length=160)
    hidden_rule = models.CharField(max_length=160, help_text="{rule} is replaced: rule: no insults")
    rule_insult_hate = models.CharField(max_length=120)
    rule_spam_ads = models.CharField(max_length=120)
    rule_real_money = models.CharField(max_length=120)
    rule_other = models.CharField(max_length=120)
    report_title = models.CharField(max_length=120)
    send_report = models.CharField(max_length=120)
    report_sent = models.CharField(max_length=160)
    write_reply = models.CharField(max_length=120)
    reply_hint = models.CharField(max_length=200)
    post_reply = models.CharField(max_length=120)
    posting = models.CharField(max_length=120)
    attach_prediction = models.CharField(max_length=200)
    prediction_in_post = models.CharField(max_length=120, help_text="{home} {score} {away} are replaced")
    about_topic = models.CharField(max_length=120)
    stat_replies = models.CharField(max_length=60)
    stat_views = models.CharField(max_length=60)
    stat_age = models.CharField(max_length=60)
    the_match = models.CharField(max_length=120)
    predict_score = models.CharField(max_length=120)
    load_more = models.CharField(max_length=120)
    topic_locked_note = models.CharField(max_length=200)
    banned_note = models.CharField(max_length=200, help_text="{until} is replaced")
    set_display_name = models.CharField(max_length=300)

    class Meta:
        verbose_name_plural = "Forum labels"
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["lang"], name="unique_forum_label_lang")]

    def __str__(self):
        return f"Forum labels ({self.lang})"
