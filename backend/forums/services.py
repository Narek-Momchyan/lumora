"""Club forums: every rule lives here, never in a view (like betting.py for football bets).

No LC moves in a forum (Rule 1). Every refusal is a coded error whose text comes from ErrorMessage in the
player's language. The limits are constants below. A player's own row is locked first in every write, so
two parallel requests of the same player cannot both pass the 30-second or the 10-topics rule.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import F
from django.utils import timezone

from errors.exceptions import CodedError
from sports import predictions
from sports.models import Match, Prediction, Team
from . import text
from .models import BannedWord, Forum, ForumBan, Post, PostLike, PostReport, Rule, Topic, TopicView

POST_INTERVAL_SECONDS = 30
TOPICS_PER_DAY = 10  # in any rolling 24 hours
TOPICS_WINDOW = timedelta(hours=24)
BODY_MIN, BODY_MAX = 1, 2000
TITLE_MIN, TITLE_MAX = 1, 120
TOP_PREDICTORS = 3
BAN_DAYS = 7  # the admin's "Ban for 7 days" action

User = get_user_model()


def refuse(code, default, status_code=None, **params):
    raise CodedError(code, default, status_code=status_code, **params)


# ---------------------------------------------------------------- what a player writes


def banned_entries():
    return [(word.key, word.inside_words) for word in BannedWord.objects.all()]


def check_text(raw, low, high, too_short, too_long, entries=None):
    """The cleaned text, or a coded refusal. Length is counted after trimming and normalising."""
    value = text.clean(raw)
    if len(value) < low:
        too_short()
    if len(value) > high:
        too_long()
    if text.has_link(value):
        refuse("post_has_link", "Links are not allowed in the forum.")
    if text.banned_hit(value, banned_entries() if entries is None else entries):
        refuse("post_banned_word", "This text contains words the forum does not allow.")
    return value


def clean_body(raw):
    return check_text(
        raw,
        BODY_MIN,
        BODY_MAX,
        lambda: refuse("post_empty", "Write something first."),
        lambda: refuse("post_too_long", "A post can have at most {max} characters.", max=BODY_MAX),
    )


def clean_title(raw):
    def bad():
        refuse("title_invalid", "A title has {min} to {max} characters.", min=TITLE_MIN, max=TITLE_MAX)

    return check_text(raw, TITLE_MIN, TITLE_MAX, bad, bad)


def check_player(user, now):
    """The player may write: not banned, and has a display name that is itself clean (never the email)."""
    ban = ForumBan.objects.filter(user=user, until__gt=now).order_by("-until").first()
    if ban:
        refuse("forum_banned", "You cannot post in the forum until {until}.", until=ban.until.strftime("%Y-%m-%d %H:%M UTC"))
    name = text.clean(user.display_name or "")
    if not name:
        refuse("display_name_required", "Set a display name in your profile before you post.")
    if "@" in name or text.has_link(name) or text.banned_hit(name, banned_entries()):
        refuse("display_name_invalid", "Your display name cannot be used in the forum. Change it first.")


def lock_player(user):
    return User.objects.select_for_update().get(pk=user.pk)


def check_rate(user, now):
    last = Post.objects.filter(author=user).order_by("-created_at").values_list("created_at", flat=True).first()
    if last and (now - last).total_seconds() < POST_INTERVAL_SECONDS:
        refuse("post_too_fast", "Wait {seconds} seconds between posts.", seconds=POST_INTERVAL_SECONDS)


# ---------------------------------------------------------------- forums


def ensure_forums():
    """One forum per club of an active competition, no duplicates however often it runs (the sync calls it)."""
    teams = Team.objects.filter(competitions__is_active=True, forum__isnull=True).distinct()
    Forum.objects.bulk_create([Forum(team=team) for team in teams], ignore_conflicts=True)


def main_competition(team):
    """The club's league (not the Champions League), used for its top predictors."""
    rows = list(team.competitions.filter(is_active=True).order_by("order", "id"))
    return next((row for row in rows if row.code != "CL"), rows[0] if rows else None)


def top_predictor_ids(forum):
    """Players in the top 3 of the club's league in the predictions season table (S4)."""
    competition = main_competition(forum.team)
    if competition is None:
        return set()
    return {row["user_id"] for row in predictions.board(competition)[:TOP_PREDICTORS]}


# ---------------------------------------------------------------- topics and posts


def attached_prediction(user, match, wanted):
    if not wanted:
        return None
    prediction = Prediction.objects.filter(user=user, match=match).first() if match else None
    if prediction is None:
        refuse("no_prediction", "You have no prediction for this match to attach.")
    return prediction


def create_topic(user, team_id, title, tag, body, match_id=None, attach_prediction=False, now=None):
    """A topic with its opening post. Returns the topic."""
    now = now or timezone.now()
    title = clean_title(title)
    body = clean_body(body)
    if tag not in Topic.Tag.values:
        refuse("invalid_tag", "Choose a tag for the topic.")
    with transaction.atomic():
        player = lock_player(user)
        check_player(player, now)
        forum = Forum.objects.filter(team_id=team_id).first()
        if forum is None:
            refuse("forum_not_found", "This forum does not exist.", status_code=404)
        match = None
        if match_id is not None:
            match = Match.objects.filter(pk=match_id).filter(home_id=team_id).first() or Match.objects.filter(
                pk=match_id, away_id=team_id
            ).first()
            if match is None:
                refuse("invalid_match", "This match is not one of the club's matches.")
        if Topic.objects.filter(author=player, created_at__gt=now - TOPICS_WINDOW).count() >= TOPICS_PER_DAY:
            refuse("too_many_topics", "You can start {max} topics a day.", max=TOPICS_PER_DAY)
        check_rate(player, now)
        prediction = attached_prediction(player, match, attach_prediction)
        topic = Topic.objects.create(
            forum=forum, author=player, title=title, tag=tag, match=match, last_post_at=now, post_count=1,
            created_at=now,
        )
        Post.objects.create(topic=topic, author=player, body=body, prediction=prediction, created_at=now)
    return topic


def create_post(user, topic_id, body, attach_prediction=False, now=None):
    """A reply. Returns the post."""
    now = now or timezone.now()
    body = clean_body(body)
    with transaction.atomic():
        player = lock_player(user)
        check_player(player, now)
        topic = Topic.objects.select_for_update().filter(pk=topic_id).first()
        if topic is None:
            refuse("topic_not_found", "This topic does not exist.", status_code=404)
        if topic.is_locked:
            refuse("topic_locked", "This topic is locked.")
        check_rate(player, now)
        prediction = attached_prediction(player, topic.match, attach_prediction)
        post = Post.objects.create(topic=topic, author=player, body=body, prediction=prediction, created_at=now)
        Topic.objects.filter(pk=topic.pk).update(post_count=F("post_count") + 1, last_post_at=now)
    return post


def get_post(post_id):
    post = Post.objects.select_related("topic").filter(pk=post_id).first()
    if post is None:
        refuse("post_not_found", "This post does not exist.", status_code=404)
    return post


def like_post(user, post_id, now=None):
    """Like a post. Doing it twice changes nothing."""
    now = now or timezone.now()
    with transaction.atomic():
        player = lock_player(user)
        check_player_banned_only(player, now)
        post = get_post(post_id)
        if post.is_hidden:
            refuse("post_hidden", "This post was hidden by a moderator.")
        PostLike.objects.get_or_create(post=post, user=player)
    return post


def unlike_post(user, post_id):
    post = get_post(post_id)
    PostLike.objects.filter(post=post, user=user).delete()
    return post


def check_player_banned_only(user, now):
    """Likes and reports need no display name, but a banned player may not do them either."""
    ban = ForumBan.objects.filter(user=user, until__gt=now).order_by("-until").first()
    if ban:
        refuse("forum_banned", "You cannot post in the forum until {until}.", until=ban.until.strftime("%Y-%m-%d %H:%M UTC"))


def report_post(user, post_id, reason, now=None):
    now = now or timezone.now()
    if reason not in Rule.values:
        refuse("invalid_report_reason", "Choose a reason for the report.")
    with transaction.atomic():
        player = lock_player(user)
        check_player_banned_only(player, now)
        post = get_post(post_id)
        if post.author_id == player.pk:
            refuse("own_post_report", "You cannot report your own post.")
        if post.is_hidden:
            refuse("post_hidden", "This post was hidden by a moderator.")
        report, created = PostReport.objects.get_or_create(post=post, reporter=player, defaults={"reason": reason})
        if not created:
            refuse("already_reported", "You already reported this post.")
    return report


def record_view(user, topic):
    """Count the player once per topic. Returns nothing; a repeat changes nothing."""
    TopicView.objects.get_or_create(topic=topic, user=user)


# ---------------------------------------------------------------- moderation (the admin calls these)


def hide_post(post, rule, moderator, now=None):
    """Hide a post and close its open reports. The text stays in the database but is never sent."""
    now = now or timezone.now()
    with transaction.atomic():
        Post.objects.filter(pk=post.pk).update(is_hidden=True, hidden_rule=rule, hidden_by=moderator, hidden_at=now)
        PostReport.objects.filter(post=post, status=PostReport.Status.OPEN).update(status=PostReport.Status.ACTIONED)


def unhide_post(post):
    Post.objects.filter(pk=post.pk).update(is_hidden=False, hidden_rule="", hidden_by=None, hidden_at=None)


def dismiss_reports(post):
    PostReport.objects.filter(post=post, status=PostReport.Status.OPEN).update(status=PostReport.Status.DISMISSED)


def ban_player(user, moderator, days=BAN_DAYS, reason="", now=None):
    now = now or timezone.now()
    return ForumBan.objects.create(user=user, until=now + timedelta(days=days), reason=reason, created_by=moderator)
