from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from . import feed


class CrashConsumer(AsyncJsonWebsocketConsumer):
    """/ws/crash: read-only and public. Bets and cash-outs go through REST."""

    async def connect(self):
        # Join first: an event that comes while the snapshot is read is then not missed.
        await self.channel_layer.group_add(feed.GROUP, self.channel_name)
        await self.accept()
        await self.send_json({"type": "snapshot", **await database_sync_to_async(feed.snapshot)()})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(feed.GROUP, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass  # nothing a client sends here does anything

    async def crash_event(self, message):
        await self.send_json({"type": message["event"], **message["data"]})
