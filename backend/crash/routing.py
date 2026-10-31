from django.urls import re_path

from .consumers import CrashConsumer

websocket_urlpatterns = [
    re_path(r"^ws/crash/?$", CrashConsumer.as_asgi()),
]
