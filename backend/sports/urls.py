from rest_framework.routers import DefaultRouter

from .views import (
    BetLabelViewSet,
    CompetitionViewSet,
    LiveLabelViewSet,
    LiveMatchViewSet,
    MarketViewSet,
    MatchViewSet,
    MatchdayViewSet,
    PopularPickViewSet,
    PredictionLabelViewSet,
    PredictionLeaderboardViewSet,
    PredictionStatsViewSet,
    PredictionViewSet,
    SportBetViewSet,
    SportsPageLabelViewSet,
    SportsUiLabelViewSet,
    StandingViewSet,
    StandingZoneViewSet,
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
sports_router.register("sports_ui_labels", SportsUiLabelViewSet, basename="sports_ui_labels")
sports_router.register("popular_picks", PopularPickViewSet, basename="popular_picks")
sports_router.register("predictions", PredictionViewSet, basename="predictions")
sports_router.register("prediction_leaderboard", PredictionLeaderboardViewSet, basename="prediction_leaderboard")
sports_router.register("prediction_stats", PredictionStatsViewSet, basename="prediction_stats")
sports_router.register("prediction_labels", PredictionLabelViewSet, basename="prediction_labels")
sports_router.register("matchdays", MatchdayViewSet, basename="matchdays")
sports_router.register("standing_zones", StandingZoneViewSet, basename="standing_zones")
sports_router.register("live_matches", LiveMatchViewSet, basename="live_matches")
sports_router.register("live_labels", LiveLabelViewSet, basename="live_labels")
