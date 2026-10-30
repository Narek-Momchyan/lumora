from django.urls import re_path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import MeViewSet, RegisterViewSet

accounts_router = DefaultRouter(trailing_slash=False)
accounts_router.register("register", RegisterViewSet, basename="register")
accounts_router.register("me", MeViewSet, basename="me")

# SimpleJWT views are plain APIViews, so they get paths instead of router entries.
token_urls = [
    re_path(r"^token/?$", TokenObtainPairView.as_view(), name="token"),
    re_path(r"^token/refresh/?$", TokenRefreshView.as_view(), name="token_refresh"),
]
