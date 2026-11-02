"""
In-memory rate limiter for sensitive endpoints.
Provides IP and identifier based sliding window rate limiting without external services.
"""
import logging
import time
from collections import defaultdict
from typing import Dict, List

from fastapi import HTTPException, Request, status

logger = logging.getLogger(__name__)

# In-memory storage: key -> list of unix timestamps
_RATE_LIMIT_STORE: Dict[str, List[float]] = defaultdict(list)


def get_client_ip(request: Request) -> str:
    """Extract client IP, inspecting X-Forwarded-For if behind a reverse proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def check_rate_limit(
    identifier: str,
    endpoint: str,
    max_requests: int = 10,
    window_seconds: int = 60,
) -> None:
    """
    Check if the identifier has exceeded max_requests in window_seconds.
    Raises HTTP 429 (Too Many Requests) if the limit is exceeded.
    """
    now = time.time()
    key = f"{endpoint}:{identifier}"
    timestamps = _RATE_LIMIT_STORE[key]

    # Purge timestamps outside sliding window
    cutoff = now - window_seconds
    _RATE_LIMIT_STORE[key] = [t for t in timestamps if t > cutoff]

    if len(_RATE_LIMIT_STORE[key]) >= max_requests:
        logger.warning(
            "Rate limit exceeded for '%s' on endpoint '%s' (%d requests in %ds)",
            identifier, endpoint, len(_RATE_LIMIT_STORE[key]), window_seconds
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per minute.",
            headers={"Retry-After": str(window_seconds)},
        )

    _RATE_LIMIT_STORE[key].append(now)


def reset_rate_limits() -> None:
    """Clear in-memory rate limit store (for testing)."""
    _RATE_LIMIT_STORE.clear()
