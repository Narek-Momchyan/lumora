from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncJsonWebsocketConsumer


class LiveFeedConsumer(AsyncJsonWebsocketConsumer):
    """A read-only, public game feed. Bets go through REST. Subclasses set `group` and `snapshot()`."""

    group = None

    def snapshot(self):
        raise NotImplementedError

    async def connect(self):
        # Join first: an event that comes while the snapshot is read is then not missed.
        await self.channel_layer.group_add(self.group, self.channel_name)
        await self.accept()
        await self.send_json({"type": "snapshot", **await database_sync_to_async(self.snapshot)()})

    async def disconnect(self, code):
        await self.channel_layer.group_discard(self.group, self.channel_name)

    async def receive(self, text_data=None, bytes_data=None, **kwargs):
        pass  # nothing a client sends here does anything

    async def live_event(self, message):
        await self.send_json({"type": message["event"], **message["data"]})
