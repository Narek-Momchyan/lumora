from rest_framework.routers import DefaultRouter

from .views import LanguageViewSet, LogoViewSet

header_router = DefaultRouter(trailing_slash=False)
header_router.register("logos", LogoViewSet, basename="logos")
header_router.register("languages", LanguageViewSet, basename="languages")
