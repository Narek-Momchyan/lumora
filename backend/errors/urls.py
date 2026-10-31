from rest_framework.routers import DefaultRouter

from .views import ErrorMessageViewSet

errors_router = DefaultRouter(trailing_slash=False)
errors_router.register("error_messages", ErrorMessageViewSet, basename="error_messages")
