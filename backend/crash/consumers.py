from base.consumers import LiveFeedConsumer
from . import feed


class CrashConsumer(LiveFeedConsumer):
    """/ws/crash: read-only and public."""

    group = feed.GROUP

    def snapshot(self):
        return feed.snapshot()
