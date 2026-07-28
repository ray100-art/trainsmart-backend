"""Rate limiting with two backends: in-memory (dev) and PostgreSQL (production).

Set RATE_LIMIT_STORAGE=database in .env (or ENVIRONMENT=production) to use the
DB-backed store. The DB store works correctly across multiple workers.
"""
import uuid
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import HTTPException, Request, status
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.core.config import settings

# ---------------------------------------------------------------------------
# In-memory backend (development / single-worker)
# ---------------------------------------------------------------------------

_lock = Lock()
_buckets: dict[str, list[datetime]] = defaultdict(list)
_last_cleanup = datetime.now(timezone.utc)
_CLEANUP_INTERVAL_SECONDS = 300
_CLEANUP_MAX_STALE_SECONDS = 600


def _client_ip(request: Request) -> str:
    if settings.TRUST_PROXY_HEADERS:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
    if request.client:
        return request.client.host
    return "unknown"


def _maybe_cleanup(now: datetime) -> None:
    global _last_cleanup
    if (now - _last_cleanup).total_seconds() < _CLEANUP_INTERVAL_SECONDS:
        return
    _last_cleanup = now
    stale_cutoff = now - timedelta(seconds=_CLEANUP_MAX_STALE_SECONDS)
    stale_keys = [k for k, v in list(_buckets.items()) if not any(t > stale_cutoff for t in v)]
    for k in stale_keys:
        del _buckets[k]


def _check_rate_limit_memory(scope: str, identifier: str, max_requests: int, window_seconds: int) -> None:
    key = f"{scope}:{identifier}"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)

    with _lock:
        _maybe_cleanup(now)
        timestamps = [t for t in _buckets[key] if t > cutoff]
        if len(timestamps) >= max_requests:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
            )
        timestamps.append(now)
        _buckets[key] = timestamps


# ---------------------------------------------------------------------------
# Database backend (production / multi-worker safe)
# ---------------------------------------------------------------------------

def _check_rate_limit_db(
    db: Session, scope: str, identifier: str, max_requests: int, window_seconds: int
) -> None:
    from app.models.rate_limit import RateLimitEvent

    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    count = (
        db.query(func.count(RateLimitEvent.id))
        .filter(
            RateLimitEvent.scope == scope,
            RateLimitEvent.identifier == identifier,
            RateLimitEvent.created_at > cutoff,
        )
        .scalar() or 0
    )
    if count >= max_requests:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests. Please try again later.",
        )
    db.add(RateLimitEvent(id=str(uuid.uuid4()), scope=scope, identifier=identifier))
    db.commit()

    import random
    if random.randint(1, 50) == 1:
        try:
            expire_cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds * 2)
            db.query(RateLimitEvent).filter(RateLimitEvent.created_at < expire_cutoff).delete()
            db.commit()
        except Exception:
            db.rollback()


def _record_event_memory(scope: str, identifier: str) -> None:
    key = f"{scope}:{identifier}"
    now = datetime.now(timezone.utc)
    with _lock:
        _buckets[key].append(now)


def _record_event_db(db: Session, scope: str, identifier: str) -> None:
    from app.models.rate_limit import RateLimitEvent
    db.add(RateLimitEvent(id=str(uuid.uuid4()), scope=scope, identifier=identifier))
    db.commit()


def _count_events_memory(scope: str, identifier: str, window_seconds: int) -> int:
    key = f"{scope}:{identifier}"
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=window_seconds)
    with _lock:
        timestamps = [t for t in _buckets[key] if t > cutoff]
        _buckets[key] = timestamps
        return len(timestamps)


def _count_events_db(db: Session, scope: str, identifier: str, window_seconds: int) -> int:
    from app.models.rate_limit import RateLimitEvent
    cutoff = datetime.now(timezone.utc) - timedelta(seconds=window_seconds)
    return (
        db.query(func.count(RateLimitEvent.id))
        .filter(
            RateLimitEvent.scope == scope,
            RateLimitEvent.identifier == identifier,
            RateLimitEvent.created_at > cutoff,
        )
        .scalar() or 0
    )


def _clear_events_memory(scope: str, identifier: str) -> None:
    key = f"{scope}:{identifier}"
    with _lock:
        _buckets.pop(key, None)


def _clear_events_db(db: Session, scope: str, identifier: str) -> None:
    from app.models.rate_limit import RateLimitEvent
    db.query(RateLimitEvent).filter(
        RateLimitEvent.scope == scope,
        RateLimitEvent.identifier == identifier,
    ).delete()
    db.commit()


# ---------------------------------------------------------------------------
# Account lockout (shared across workers when DB-backed)
# ---------------------------------------------------------------------------

LOGIN_FAIL_SCOPE = "login_fail"


def check_account_lockout(db: Session, identifier: str) -> None:
    """Raise 429 if this account has too many recent failed logins."""
    window = settings.LOGIN_LOCKOUT_MINUTES * 60
    if settings.rate_limit_use_database:
        count = _count_events_db(db, LOGIN_FAIL_SCOPE, identifier, window)
    else:
        count = _count_events_memory(LOGIN_FAIL_SCOPE, identifier, window)
    if count >= settings.LOGIN_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=(
                f"Account temporarily locked. Try again in "
                f"{settings.LOGIN_LOCKOUT_MINUTES} minute(s)."
            ),
        )


def record_failed_login(db: Session, identifier: str) -> None:
    if settings.rate_limit_use_database:
        _record_event_db(db, LOGIN_FAIL_SCOPE, identifier)
    else:
        _record_event_memory(LOGIN_FAIL_SCOPE, identifier)


def clear_failed_logins(db: Session, identifier: str) -> None:
    if settings.rate_limit_use_database:
        _clear_events_db(db, LOGIN_FAIL_SCOPE, identifier)
    else:
        _clear_events_memory(LOGIN_FAIL_SCOPE, identifier)


# ---------------------------------------------------------------------------
# Public helpers called by routers
# ---------------------------------------------------------------------------

def check_rate_limit(
    request: Request,
    scope: str,
    max_requests: int,
    window_seconds: int,
    db: Session | None = None,
) -> None:
    identifier = _client_ip(request)
    use_db = settings.rate_limit_use_database

    if use_db and db is not None:
        _check_rate_limit_db(db, scope, identifier, max_requests, window_seconds)
    else:
        _check_rate_limit_memory(scope, identifier, max_requests, window_seconds)


def check_verify_rate_limit(request: Request, db: Session | None = None) -> None:
    check_rate_limit(
        request,
        "verify",
        max_requests=settings.VERIFY_RATE_LIMIT_MAX,
        window_seconds=settings.VERIFY_RATE_LIMIT_WINDOW_SECONDS,
        db=db,
    )


def check_login_ip_rate_limit(request: Request, db: Session | None = None) -> None:
    check_rate_limit(
        request,
        "login_ip",
        max_requests=settings.LOGIN_MAX_ATTEMPTS * 3,
        window_seconds=60,
        db=db,
    )


def check_forgot_password_rate_limit(request: Request, db: Session | None = None) -> None:
    check_rate_limit(
        request,
        "forgot_password",
        max_requests=5,
        window_seconds=300,
        db=db,
    )
