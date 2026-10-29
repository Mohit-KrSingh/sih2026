"""Redis-backed sliding window rate limiter."""

import time
import uuid

import redis
from fastapi import Depends, HTTPException, Request, status

from app.config import get_settings
from app.db import get_redis


def _extract_client_ip(request: Request) -> str:
    """Extract real client IP address from request headers or socket."""
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take the first IP if a comma-separated list is present
        return forwarded_for.split(",")[0].strip()
    if request.client and request.client.host:
        return request.client.host
    return "127.0.0.1"


class RateLimiter:
    """FastAPI dependency for sliding-window rate limiting via Redis."""

    def __init__(
        self,
        times: int = 10,
        seconds: int = 60,
        label: str = "default",
    ) -> None:
        self.times = times
        self.seconds = seconds
        self.label = label

    def __call__(
        self,
        request: Request,
        redis_client: redis.Redis = Depends(get_redis),
    ) -> None:
        settings = get_settings()
        if not settings.RATE_LIMIT_ENABLED:
            return

        client_ip = _extract_client_ip(request)
        key = f"ratelimit:{self.label}:{client_ip}"
        now = time.time()
        window_start = now - self.seconds

        # Redis pipeline for atomic sliding window operations
        pipe = redis_client.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        member = f"{now}-{uuid.uuid4().hex[:8]}"
        pipe.zadd(key, {member: now})
        pipe.zcard(key)
        pipe.expire(key, self.seconds + 5)

        results = pipe.execute()
        current_count = int(results[2])

        if current_count > self.times:
            # Over the limit: retrieve oldest timestamp in the current window to compute Retry-After
            oldest_entries = redis_client.zrange(key, 0, 0, withscores=True)
            if oldest_entries:
                oldest_ts = float(oldest_entries[0][1])
                retry_after = max(1, int(self.seconds - (now - oldest_ts)))
            else:
                retry_after = self.seconds

            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for {self.label}. Please try again later.",
                headers={"Retry-After": str(retry_after)},
            )


def reset_rate_limit(
    redis_client: redis.Redis,
    label: str,
    client_ip: str | None = None,
) -> None:
    """Helper to clear rate limit records for testing purposes."""
    if client_ip:
        key = f"ratelimit:{label}:{client_ip}"
        redis_client.delete(key)
    else:
        keys = redis_client.keys(f"ratelimit:{label}:*")
        if keys:
            redis_client.delete(*keys)
