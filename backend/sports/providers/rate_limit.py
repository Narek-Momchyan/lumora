import time
from collections import deque


class RateLimiter:
    """At most `per_minute` calls in any 60 seconds (football-data.org's free plan allows 10).

    `wait()` sleeps until the next call may go out. The clock and the sleep are injected, so a
    test can check the waiting without really sleeping.
    """

    def __init__(self, per_minute=10, clock=time.monotonic, sleep=time.sleep, window=60.0):
        self.per_minute = per_minute
        self.window = window
        self.clock = clock
        self.sleep = sleep
        self.calls = deque()

    def wait(self):
        now = self.clock()
        while self.calls and now - self.calls[0] >= self.window:
            self.calls.popleft()
        if len(self.calls) >= self.per_minute:
            pause = self.window - (now - self.calls[0])
            if pause > 0:
                self.sleep(pause)
            now = self.clock()
            self.calls.popleft()
        self.calls.append(now)

    def pause(self, seconds):
        """The server asked us to wait (429): nothing goes out until then."""
        self.sleep(seconds)
