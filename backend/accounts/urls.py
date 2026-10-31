from rest_framework.routers import DefaultRouter

from .views import LogoutViewSet, MeViewSet, RegisterViewSet, TokenViewSet

accounts_router = DefaultRouter(trailing_slash=False)
accounts_router.register("register", RegisterViewSet, basename="register")
accounts_router.register("token", TokenViewSet, basename="token")
accounts_router.register("logout", LogoutViewSet, basename="logout")
accounts_router.register("me", MeViewSet, basename="me")
