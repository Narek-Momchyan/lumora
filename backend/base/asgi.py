"""
ASGI config for base project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import OriginValidator
from django.conf import settings
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "base.settings")

django_application = get_asgi_application()

from crash.routing import websocket_urlpatterns as crash_urlpatterns  # noqa: E402  (needs the apps loaded above)
from roulette.routing import websocket_urlpatterns as roulette_urlpatterns  # noqa: E402
from sports.routing import websocket_urlpatterns as sports_urlpatterns  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_application,
        # Sites other than ours can't open the socket, even though it needs no login.
        "websocket": OriginValidator(
            URLRouter(crash_urlpatterns + roulette_urlpatterns + sports_urlpatterns), settings.CSRF_TRUSTED_ORIGINS
        ),
    }
)
