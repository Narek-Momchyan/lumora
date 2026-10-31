from rest_framework.routers import DefaultRouter

from .views import GameCategoryViewSet, GameViewSet, LobbyPageLabelViewSet

games_router = DefaultRouter(trailing_slash=False)
games_router.register("games", GameViewSet, basename="games")
games_router.register("game_categories", GameCategoryViewSet, basename="game_categories")
games_router.register("lobby_page_labels", LobbyPageLabelViewSet, basename="lobby_page_labels")
