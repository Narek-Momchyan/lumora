"""
URL configuration for base project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from rest_framework.permissions import AllowAny
from rest_framework.routers import APIRootView, DefaultRouter

from accounts.urls import accounts_router
from base.media import serve_media
from crash.urls import crash_router
from errors.urls import errors_router
from fairness.urls import fairness_router
from games.urls import games_router
from header.urls import header_router
from leaderboard.urls import leaderboard_router
from roulette.urls import roulette_router
from slots.urls import slots_router
from sports.urls import sports_router
from wallet.urls import wallet_router


class PublicAPIRootView(APIRootView):
    permission_classes = [AllowAny]  # the /api/ index only lists URLs


class OptionalSlashRouter(DefaultRouter):
    APIRootView = PublicAPIRootView

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.trailing_slash = "/?"


router = OptionalSlashRouter()

router.registry.extend(accounts_router.registry)
router.registry.extend(wallet_router.registry)
router.registry.extend(fairness_router.registry)
router.registry.extend(games_router.registry)
router.registry.extend(crash_router.registry)
router.registry.extend(roulette_router.registry)
router.registry.extend(slots_router.registry)
router.registry.extend(leaderboard_router.registry)
router.registry.extend(header_router.registry)
router.registry.extend(errors_router.registry)
router.registry.extend(sports_router.registry)

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
] + static(settings.MEDIA_URL, view=serve_media, document_root=settings.MEDIA_ROOT)
