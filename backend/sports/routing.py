from django.urls import re_path

from .consumers import SportsConsumer

websocket_urlpatterns = [
    re_path(r"^ws/sports/?$", SportsConsumer.as_asgi()),
]
