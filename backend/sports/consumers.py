from base.consumers import LiveFeedConsumer
from . import feed


class SportsConsumer(LiveFeedConsumer):
    """/ws/sports: the live scores. Read-only and public, like /ws/crash."""

    group = feed.GROUP

    def snapshot(self):
        return feed.snapshot()
