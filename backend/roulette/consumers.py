from base.consumers import LiveFeedConsumer
from . import feed


class RouletteConsumer(LiveFeedConsumer):
    """/ws/roulette: read-only and public."""

    group = feed.GROUP

    def snapshot(self):
        return feed.snapshot()
