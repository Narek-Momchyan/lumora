from rest_framework.routers import DefaultRouter

from .views import RouletteBetViewSet, RoulettePageLabelViewSet, RouletteRoundViewSet

roulette_router = DefaultRouter(trailing_slash=False)
roulette_router.register("roulette_bets", RouletteBetViewSet, basename="roulette_bets")
roulette_router.register("roulette_rounds", RouletteRoundViewSet, basename="roulette_rounds")
roulette_router.register("roulette_page_labels", RoulettePageLabelViewSet, basename="roulette_page_labels")
