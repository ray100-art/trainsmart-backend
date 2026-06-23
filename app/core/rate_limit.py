"""Thread-safe in-memory rate limiter keyed by client identifier."""
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = Lock()
_buckets: dict[str, list[datetime]] = defaultdict(list)


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def check_rate_limit(request: Request, scope: str, max_requests: int, window_seconds: int) -> None:
    """Raise 429 if the client exceeds max_requests within window_seconds."""
    key = f"{scope}:{_client_ip(request)}"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)

    with _lock:
        timestamps = [t for t in _buckets[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
        timestamps.append(now)
        _buckets[key] = timestamps


def check_verify_rate_limit(request: Request) -> None:
    check_rate_limit(
        request,
        "verify",
        max_requests=settings.VERIFY_RATE_LIMIT_MAX,
        window_seconds=settings.VERIFY_RATE_LIMIT_WINDOW_SECONDS,
    )


def check_login_ip_rate_limit(request: Request) -> None:
    check_rate_limit(request, "login_ip", max_requests=settings.LOGIN_MAX_ATTEMPTS * 3, window_seconds=60)
