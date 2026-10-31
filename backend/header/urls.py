from rest_framework.routers import DefaultRouter

from .views import HeaderLabelViewSet, LanguageViewSet, LogoViewSet, SidebarItemViewSet

header_router = DefaultRouter(trailing_slash=False)
header_router.register("logos", LogoViewSet, basename="logos")
header_router.register("languages", LanguageViewSet, basename="languages")
header_router.register("sidebar_items", SidebarItemViewSet, basename="sidebar_items")
header_router.register("header_labels", HeaderLabelViewSet, basename="header_labels")
