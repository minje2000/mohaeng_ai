from __future__ import annotations

from collections import defaultdict, deque
from threading import Lock
import time

from app.core.config import settings


class RateLimitService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._buckets: dict[str, deque[float]] = defaultdict(deque)
        self.window_seconds = max(1, int(settings.CHAT_RATE_LIMIT_WINDOW_SECONDS))
        self.max_requests = max(1, int(settings.CHAT_RATE_LIMIT_MAX_REQUESTS))

    def check(self, key: str) -> tuple[bool, int]:
        now = time.time()
        with self._lock:
            bucket = self._buckets[key]
            while bucket and now - bucket[0] > self.window_seconds:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                retry_after = int(self.window_seconds - (now - bucket[0])) if bucket else self.window_seconds
                return False, max(1, retry_after)
            bucket.append(now)
            return True, 0
