from django.db.models import Count, Exists, OuterRef, Q, Subquery, Sum
from django.db.models.functions import Coalesce
from django.utils.dateparse import parse_datetime
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import viewsets

from base.language import get_lang
from base.views import FilteredReadOnlyViewSet, LangFilteredViewSet
from sports.models import Team
from . import services
from .models import Forum, ForumLabel, Post, PostLike, Topic
from .serializers import (
    ForumLabelSerializer,
    ForumSerializer,
    PostRequestSerializer,
    PostSerializer,
    ReportRequestSerializer,
    TopicRequestSerializer,
    TopicSerializer,
)

class ForumViewSet(FilteredReadOnlyViewSet):
    """The clubs' forums with their topic and post counts (?competition=PL for one league). The id is the club's id."""

    queryset = (
        Forum.objects.filter(team__in=Team.objects.filter(competitions__is_active=True))
        .select_related("team")
        .prefetch_related("team__names", "team__competitions")
        .annotate(topic_total=Count("topics", distinct=True), post_total=Coalesce(Sum("topics__post_count"), 0))
        .order_by("team__name")
    )
    serializer_class = ForumSerializer
    lookup_field = "team_id"

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": get_lang(self.request)}

    def get_queryset(self):
        qs = super().get_queryset()
        competition = self.request.query_params.get("competition")
        if competition:
            qs = qs.filter(team__in=Team.objects.filter(competitions__code=competition))
        return qs


def cut(qs, before):
    """Keyset paging for the latest sort: `before` is `<last_post_at>_<id>` of the last row you have."""
    stamp, _, row_id = (before or "").rpartition("_")
    when = parse_datetime(stamp) if stamp else None
    if not (when and row_id.isdigit()):
        return qs.none()
    return qs.filter(Q(last_post_at__lt=when) | Q(last_post_at=when, id__lt=int(row_id)))


SORTS = {
    "latest": ("-is_pinned", "-last_post_at", "-id"),
    "replies": ("-is_pinned", "-post_count", "-id"),
    "views": ("-is_pinned", "-views", "-id"),
}


class TopicViewSet(FilteredReadOnlyViewSet):
    """GET ?forum=<club id>&tag=&sort=latest|replies|views: at most 50, pinned first. `?before=<last_post_at>_<id>`
    gives the next 50 of the latest sort; the other sorts return their top 50. POST creates a topic."""

    queryset = (
        Topic.objects.select_related("author", "forum")
        .annotate(
            views=Count("viewers", distinct=True),
            last_author=Subquery(Post.objects.filter(topic=OuterRef("pk")).order_by("-id").values("author__display_name")[:1]),
        )
    )
    serializer_class = TopicSerializer
    list_limit = 50

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "lang": get_lang(self.request)}

    def get_queryset(self):
        qs = super().get_queryset()
        params = self.request.query_params
        if self.action != "list":
            return qs
        forum = params.get("forum")
        if not (forum or "").isdigit():
            return qs.none()
        qs = qs.filter(forum__team_id=forum)
        if params.get("tag"):
            qs = qs.filter(tag=params["tag"])
        sort = params.get("sort", "latest")
        if sort not in SORTS:
            return qs.none()
        if "before" in params:
            if sort != "latest":
                return qs.none()
            qs = cut(qs, params["before"])
        return qs.order_by(*SORTS[sort])

    def retrieve(self, request, *args, **kwargs):
        topic = self.get_object()
        services.record_view(request.user, topic)
        topic = self.get_queryset().get(pk=topic.pk)  # the count now includes this player
        return Response(self.get_serializer(topic).data)

    def create(self, request, *args, **kwargs):
        serializer = TopicRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        topic = services.create_topic(
            request.user, data["forum"], data["title"], data["tag"], data["body"], data.get("match"),
            data["attach_prediction"],
        )
        return Response(self.get_serializer(self.get_queryset().get(pk=topic.pk)).data, status=status.HTTP_201_CREATED)


class PostViewSet(FilteredReadOnlyViewSet):
    """GET ?topic=<id>: oldest first, at most 100; `?after=<last post id>` gives the next ones. A hidden post has
    no text. POST creates a reply; POST / DELETE /<id>/like likes and unlikes."""

    serializer_class = PostSerializer
    list_limit = 100

    def get_queryset(self):
        user = self.request.user
        qs = (
            Post.objects.select_related("author", "topic", "prediction__match__home", "prediction__match__away")
            .annotate(
                like_total=Count("likes", distinct=True),
                liked_by_me=Exists(PostLike.objects.filter(post=OuterRef("pk"), user=user)),
            )
            .order_by("id")
        )
        if self.action != "list":
            return qs
        params = self.request.query_params
        topic = params.get("topic")
        if not (topic or "").isdigit():
            return qs.none()
        qs = qs.filter(topic_id=topic)
        if "after" in params:
            if not params["after"].isdigit():
                return qs.none()
            qs = qs.filter(id__gt=int(params["after"]))
        return qs

    def get_serializer_context(self):
        context = {**super().get_serializer_context(), "lang": get_lang(self.request), "user_id": self.request.user.pk}
        topic = self.request.query_params.get("topic")
        if (topic or "").isdigit():
            row = Topic.objects.select_related("forum__team").filter(pk=topic).first()
            if row:
                context["top_predictors"] = services.top_predictor_ids(row.forum)
        return context

    def create(self, request, *args, **kwargs):
        serializer = PostRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        post = services.create_post(request.user, data["topic"], data["body"], data["attach_prediction"])
        row = self.get_queryset().get(pk=post.pk)
        context = {**self.get_serializer_context(), "top_predictors": services.top_predictor_ids(row.topic.forum)}
        return Response(PostSerializer(row, context=context).data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post", "delete"])
    def like(self, request, pk=None):
        if request.method == "POST":
            services.like_post(request.user, int(pk))
        else:
            services.unlike_post(request.user, int(pk))
        row = self.get_queryset().get(pk=pk)
        return Response({"id": row.pk, "likes": row.like_total, "liked_by_me": row.liked_by_me})


class PostReportViewSet(viewsets.ViewSet):
    """POST {post, reason}: report a post (insult_hate, spam_ads, real_money, other). One report per player and post."""

    def create(self, request):
        serializer = ReportRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report = services.report_post(request.user, serializer.validated_data["post"], serializer.validated_data["reason"])
        return Response({"id": report.pk, "post": report.post_id, "reason": report.reason}, status=status.HTTP_201_CREATED)


class ForumLabelViewSet(LangFilteredViewSet):
    queryset = ForumLabel.objects.all()
    serializer_class = ForumLabelSerializer
