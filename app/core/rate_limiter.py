import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict, deque
from uuid import uuid4

import redis

from app.core.config import settings


class RateLimiter(ABC):
    @abstractmethod
    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        raise NotImplementedError

    @abstractmethod
    def reset(self) -> None:
        raise NotImplementedError


class InMemoryRateLimiter(RateLimiter):
    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        now = time.time()
        window_start = now - window_seconds
        with self._lock:
            queue = self._events[key]
            while queue and queue[0] <= window_start:
                queue.popleft()

            if len(queue) >= limit:
                retry_after = max(1, int(queue[0] + window_seconds - now))
                return False, retry_after

            queue.append(now)
            return True, 0

    def reset(self) -> None:
        with self._lock:
            self._events.clear()


class RedisRateLimiter(RateLimiter):
    def __init__(self, redis_url: str, prefix: str = "rl") -> None:
        self._client = redis.Redis.from_url(
            redis_url,
            socket_connect_timeout=0.2,
            socket_timeout=0.2,
            decode_responses=False,
        )
        self._prefix = prefix

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        redis_key = f"{self._prefix}:{key}"
        now_ms = int(time.time() * 1000)
        window_ms = window_seconds * 1000
        boundary = now_ms - window_ms

        pipe = self._client.pipeline()
        pipe.zremrangebyscore(redis_key, 0, boundary)
        pipe.zcard(redis_key)
        _, current_count = pipe.execute()

        if current_count >= limit:
            oldest = self._client.zrange(redis_key, 0, 0, withscores=True)
            if oldest:
                oldest_score = int(oldest[0][1])
                retry_after = max(1, int((oldest_score + window_ms - now_ms) / 1000))
            else:
                retry_after = max(1, window_seconds)
            return False, retry_after

        member = f"{now_ms}:{uuid4().hex}".encode()
        pipe = self._client.pipeline()
        pipe.zadd(redis_key, {member: now_ms})
        pipe.expire(redis_key, window_seconds + 5)
        pipe.execute()
        return True, 0

    def reset(self) -> None:
        keys = self._client.keys(f"{self._prefix}:*")
        if keys:
            self._client.delete(*keys)


class FallbackRateLimiter(RateLimiter):
    def __init__(self, primary: RateLimiter, fallback: RateLimiter) -> None:
        self._primary = primary
        self._fallback = fallback

    def allow(self, key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
        try:
            return self._primary.allow(key=key, limit=limit, window_seconds=window_seconds)
        except Exception:
            return self._fallback.allow(key=key, limit=limit, window_seconds=window_seconds)

    def reset(self) -> None:
        try:
            self._primary.reset()
        except Exception:
            pass
        self._fallback.reset()


def _build_rate_limiter() -> RateLimiter:
    backend = settings.rate_limit_backend.strip().lower()
    memory = InMemoryRateLimiter()
    if backend == "memory":
        return memory
    if backend == "redis":
        redis_limiter = RedisRateLimiter(redis_url=settings.rate_limit_redis_url)
        return FallbackRateLimiter(primary=redis_limiter, fallback=memory)
    return memory


rate_limiter: RateLimiter = _build_rate_limiter()
