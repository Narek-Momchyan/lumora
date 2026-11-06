from rest_framework import serializers

from base.serializers import ModelSerializer
from sports.serializers import TeamSerializer
from .models import Forum, ForumLabel, Post, Topic


def author_data(user):
    """Who wrote it: the display name only, never the email or a part of it, and no user id (ids are
    sequential, so they would show how many players there are and let anyone walk through them). `name` is
    null for a player who has none; the page then shows the plain "Player" text from the labels."""
    return {"name": user.display_name or None}


class ForumLabelSerializer(ModelSerializer):
    class Meta:
        model = ForumLabel
        fields = "__all__"


class ForumSerializer(ModelSerializer):
    """A club's forum. Its id is the club's id (the URL is /forums/<team id>)."""

    id = serializers.IntegerField(source="team_id")
    team = TeamSerializer()
    competition = serializers.SerializerMethodField()
    topics = serializers.IntegerField(source="topic_total", read_only=True, default=0)
    posts = serializers.IntegerField(source="post_total", read_only=True, default=0)

    class Meta:
        model = Forum
        fields = ["id", "team", "competition", "topics", "posts"]

    def get_competition(self, obj):
        """The club's league code (not the Champions League), from the prefetched competitions."""
        rows = sorted((row for row in obj.team.competitions.all() if row.is_active), key=lambda row: (row.order, row.id))
        league = next((row for row in rows if row.code != "CL"), rows[0] if rows else None)
        return league.code if league else None


class TopicSerializer(ModelSerializer):
    forum = serializers.IntegerField(source="forum.team_id")
    author = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    views = serializers.IntegerField(read_only=True, default=0)
    last_author = serializers.SerializerMethodField()

    class Meta:
        model = Topic
        fields = [
            "id", "forum", "title", "tag", "match", "is_pinned", "is_locked", "author", "replies", "views",
            "post_count", "created_at", "last_post_at", "last_author",
        ]

    def get_author(self, obj):
        return author_data(obj.author)

    def get_replies(self, obj):
        return max(0, obj.post_count - 1)

    def get_last_author(self, obj):
        return getattr(obj, "last_author", None) or None


class PostSerializer(ModelSerializer):
    """A post. A hidden post carries no text at all: `body` is null and `hidden_rule` says which rule."""

    author = serializers.SerializerMethodField()
    body = serializers.SerializerMethodField()
    hidden = serializers.BooleanField(source="is_hidden")
    is_author = serializers.SerializerMethodField()  # the topic's author ("Author" tag)
    is_mine = serializers.SerializerMethodField()
    top_predictor = serializers.SerializerMethodField()
    likes = serializers.IntegerField(source="like_total", read_only=True, default=0)
    liked_by_me = serializers.BooleanField(read_only=True, default=False)
    prediction = serializers.SerializerMethodField()

    class Meta:
        model = Post
        fields = [
            "id", "topic", "author", "is_author", "is_mine", "top_predictor", "created_at", "hidden",
            "hidden_rule", "body", "likes", "liked_by_me", "prediction",
        ]

    def get_author(self, obj):
        return author_data(obj.author)

    def get_body(self, obj):
        return None if obj.is_hidden else obj.body

    def get_is_author(self, obj):
        return obj.author_id == obj.topic.author_id

    def get_is_mine(self, obj):
        return obj.author_id == self.context["user_id"]

    def get_top_predictor(self, obj):
        return obj.author_id in self.context.get("top_predictors", ())

    def get_prediction(self, obj):
        if obj.is_hidden or obj.prediction is None:
            return None
        match = obj.prediction.match
        context = {"lang": self.context["lang"]}
        return {
            "home_goals": obj.prediction.home_goals,
            "away_goals": obj.prediction.away_goals,
            "home": TeamSerializer(match.home, context=context).data,
            "away": TeamSerializer(match.away, context=context).data,
        }


class TopicRequestSerializer(serializers.Serializer):
    forum = serializers.IntegerField()
    title = serializers.CharField(allow_blank=True, trim_whitespace=False)
    tag = serializers.CharField(allow_blank=True)
    body = serializers.CharField(allow_blank=True, trim_whitespace=False)
    match = serializers.IntegerField(required=False, allow_null=True)
    attach_prediction = serializers.BooleanField(required=False, default=False)


class PostRequestSerializer(serializers.Serializer):
    topic = serializers.IntegerField()
    body = serializers.CharField(allow_blank=True, trim_whitespace=False)
    attach_prediction = serializers.BooleanField(required=False, default=False)


class ReportRequestSerializer(serializers.Serializer):
    post = serializers.IntegerField()
    reason = serializers.CharField(allow_blank=True)
