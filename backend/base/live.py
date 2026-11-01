"""What the live games share: one runner at a time, and the feed to the WebSocket clients."""

import logging

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import connection

logger = logging.getLogger(__name__)


def acquire_lock(key):
    """Only one runner of a game at a time. PostgreSQL frees the lock when the process's connection ends."""
    with connection.cursor() as cursor:
        cursor.execute("SELECT pg_try_advisory_lock(%s)", [key])
        return cursor.fetchone()[0]


def publish(group, event, data):
    """Send an event to every client. If Redis is down the game goes on without a live feed."""
    try:
        async_to_sync(get_channel_layer().group_send)(group, {"type": "live.event", "event": event, "data": data})
    except Exception:
        logger.exception("Could not publish %s", event)


def player_name(user):
    return user.display_name or user.email.split("@")[0]
