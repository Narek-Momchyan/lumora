from rest_framework.routers import DefaultRouter

from .views import GameViewSet

games_router = DefaultRouter(trailing_slash=False)
games_router.register("games", GameViewSet, basename="games")
