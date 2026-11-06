from rest_framework.routers import DefaultRouter

from .views import ForumLabelViewSet, ForumViewSet, PostReportViewSet, PostViewSet, TopicViewSet

forums_router = DefaultRouter(trailing_slash=False)
forums_router.register("forums", ForumViewSet, basename="forums")
forums_router.register("topics", TopicViewSet, basename="topics")
forums_router.register("posts", PostViewSet, basename="posts")
forums_router.register("post_reports", PostReportViewSet, basename="post_reports")
forums_router.register("forum_labels", ForumLabelViewSet, basename="forum_labels")
