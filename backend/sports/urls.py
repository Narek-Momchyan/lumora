from rest_framework.routers import DefaultRouter

from .views import CompetitionViewSet, MatchViewSet, SportsPageLabelViewSet, StandingViewSet, TeamViewSet

sports_router = DefaultRouter(trailing_slash=False)
sports_router.register("sports_page_labels", SportsPageLabelViewSet, basename="sports_page_labels")
sports_router.register("competitions", CompetitionViewSet, basename="competitions")
sports_router.register("teams", TeamViewSet, basename="teams")
sports_router.register("matches", MatchViewSet, basename="matches")
sports_router.register("standings", StandingViewSet, basename="standings")
