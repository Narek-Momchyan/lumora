from rest_framework.routers import DefaultRouter

from .views import (
    BetLabelViewSet,
    CompetitionViewSet,
    MarketViewSet,
    MatchViewSet,
    SportBetViewSet,
    SportsPageLabelViewSet,
    StandingViewSet,
    TeamViewSet,
)

sports_router = DefaultRouter(trailing_slash=False)
sports_router.register("sports_page_labels", SportsPageLabelViewSet, basename="sports_page_labels")
sports_router.register("competitions", CompetitionViewSet, basename="competitions")
sports_router.register("teams", TeamViewSet, basename="teams")
sports_router.register("matches", MatchViewSet, basename="matches")
sports_router.register("standings", StandingViewSet, basename="standings")
sports_router.register("markets", MarketViewSet, basename="markets")
sports_router.register("sport_bets", SportBetViewSet, basename="sport_bets")
sports_router.register("bet_labels", BetLabelViewSet, basename="bet_labels")
