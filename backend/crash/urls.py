from rest_framework.routers import DefaultRouter

from .views import CrashBetViewSet

crash_router = DefaultRouter(trailing_slash=False)
crash_router.register("crash_bets", CrashBetViewSet, basename="crash_bets")
