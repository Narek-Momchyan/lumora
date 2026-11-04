from rest_framework.routers import DefaultRouter

from .views import SportsPageLabelViewSet

sports_router = DefaultRouter(trailing_slash=False)
sports_router.register("sports_page_labels", SportsPageLabelViewSet, basename="sports_page_labels")
