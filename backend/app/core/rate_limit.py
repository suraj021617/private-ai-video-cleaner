"""Simple in-memory sliding-window rate limiter for auth endpoints."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock

from app.core.errors import AppError


class RateLimiter:
    def __init__(self, *, max_attempts: int, window_seconds: int) -> None:
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self._lock:
            bucket = self._events[key]
            cutoff = now - self.window_seconds
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_attempts:
                raise AppError(
                    code="rate_limited",
                    message="Too many attempts. Please try again later.",
                    status_code=429,
                    details={"retry_after_seconds": self.window_seconds},
                )
            bucket.append(now)


_auth_limiter: RateLimiter | None = None


def get_auth_rate_limiter(max_attempts: int, window_seconds: int) -> RateLimiter:
    global _auth_limiter
    if (
        _auth_limiter is None
        or _auth_limiter.max_attempts != max_attempts
        or _auth_limiter.window_seconds != window_seconds
    ):
        _auth_limiter = RateLimiter(
            max_attempts=max_attempts,
            window_seconds=window_seconds,
        )
    return _auth_limiter
