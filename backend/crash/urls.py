from rest_framework.routers import DefaultRouter

from .views import CrashBetViewSet, CrashPageLabelViewSet, CrashRoundViewSet

crash_router = DefaultRouter(trailing_slash=False)
crash_router.register("crash_bets", CrashBetViewSet, basename="crash_bets")
crash_router.register("crash_rounds", CrashRoundViewSet, basename="crash_rounds")
crash_router.register("crash_page_labels", CrashPageLabelViewSet, basename="crash_page_labels")
