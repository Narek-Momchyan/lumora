from rest_framework.routers import DefaultRouter

from .views import SeedPairViewSet

fairness_router = DefaultRouter(trailing_slash=False)
fairness_router.register("seeds", SeedPairViewSet, basename="seeds")
