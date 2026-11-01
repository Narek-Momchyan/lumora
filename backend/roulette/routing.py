from django.urls import re_path

from .consumers import RouletteConsumer

websocket_urlpatterns = [
    re_path(r"^ws/roulette/?$", RouletteConsumer.as_asgi()),
]
