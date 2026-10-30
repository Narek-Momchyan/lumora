from rest_framework.routers import DefaultRouter

from .views import LeaderboardViewSet

leaderboard_router = DefaultRouter(trailing_slash=False)
leaderboard_router.register("leaderboard", LeaderboardViewSet, basename="leaderboard")
