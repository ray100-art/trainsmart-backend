import uuid
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from threading import Lock

from sqlalchemy.orm import Session
from fastapi import BackgroundTasks, HTTPException, status

from app.models.user import User
from app.schemas.auth import UserCreate
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.services.email_service import send_welcome_email

# ── Valid roles ────────────────────────────────────────────────────────────────
VALID_ROLES = {
    "ROLE_TRAINER",
    "ROLE_COUNTY_OFFICER",
    "ROLE_NATIONAL_ADMIN",
    "ROLE_ME_MANAGER",
    "ROLE_SYSTEM_ADMIN",
    "ROLE_TRAINEE",
}

# ── In-memory brute force tracker ─────────────────────────────────────────────
# Structure: { identifier: { "count": int, "locked_until": datetime | None } }
# NOTE: This resets on server restart. For production, replace with a Redis-backed
# store so lockouts survive restarts and work across multiple server processes.
_login_attempts: dict = defaultdict(lambda: {"count": 0, "locked_until": None})
_lock = Lock()

# A valid pre-hashed bcrypt string used ONLY for constant-time dummy comparison
# when a username doesn't exist (prevents timing-based user enumeration attacks).
# This is the bcrypt hash of the string "timing_attack_prevention_dummy".
_DUMMY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsuQSm0l8AKKqFvpNP1M0SnbLpqu"


def _check_rate_limit(identifier: str) -> None:
    """Block login if too many failed attempts. Thread-safe."""
    with _lock:
        record = _login_attempts[identifier]
        now = datetime.now(timezone.utc)

        if record["locked_until"] and now < record["locked_until"]:
            remaining = int((record["locked_until"] - now).total_seconds() / 60) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Account temporarily locked due to too many failed attempts. "
                       f"Try again in {remaining} minute(s).",
            )

        # If lockout has expired, reset the counter
        if record["locked_until"] and now >= record["locked_until"]:
            record["count"] = 0
            record["locked_until"] = None


def _record_failed_attempt(identifier: str) -> None:
    """Increment failure counter and lock if threshold reached."""
    with _lock:
        record = _login_attempts[identifier]
        record["count"] += 1
        if record["count"] >= settings.LOGIN_MAX_ATTEMPTS:
            record["locked_until"] = (
                datetime.now(timezone.utc)
                + timedelta(minutes=settings.LOGIN_LOCKOUT_MINUTES)
            )


def _clear_attempts(identifier: str) -> None:
    """Clear failures on successful login."""
    with _lock:
        _login_attempts.pop(identifier, None)


# ── Validators ────────────────────────────────────────────────────────────────

def _validate_password_strength(password: str) -> None:
    """Enforce minimum password security requirements."""
    errors = []
    if len(password) < 8:
        errors.append("at least 8 characters")
    if not any(c.isupper() for c in password):
        errors.append("at least one uppercase letter")
    if not any(c.islower() for c in password):
        errors.append("at least one lowercase letter")
    if not any(c.isdigit() for c in password):
        errors.append("at least one number")
    if not any(c in "!@#$%^&*()_+-=[]{}|;':\",./<>?" for c in password):
        errors.append("at least one special character")
    if errors:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Password must contain: {', '.join(errors)}.",
        )


def _validate_role(role: str) -> None:
    if role not in VALID_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Valid roles: {', '.join(sorted(VALID_ROLES))}",
        )


# ── User creation ─────────────────────────────────────────────────────────────

def create_user(db: Session, data: UserCreate, background_tasks: BackgroundTasks | None = None) -> User:
    _validate_password_strength(data.password)
    _validate_role(data.role)

    # Check uniqueness — use a generic message to avoid user enumeration
    existing = db.query(User).filter(
        (User.username == data.username) | (User.email == data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that username or email already exists.",
        )

    user = User(
        id=str(uuid.uuid4()),
        username=data.username.strip().lower(),
        email=data.email.strip().lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        county=data.county,
        staff_number=data.staff_number,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send welcome email with credentials (fire-and-forget — never block account creation)
    if settings.EMAIL_ENABLED and user.email:
        if background_tasks:
            background_tasks.add_task(
                send_welcome_email,
                to_email=user.email,
                full_name=user.full_name,
                username=user.username,
                password=data.password,
                role=user.role,
                county=user.county,
            )
        else:
            try:
                send_welcome_email(
                    to_email=user.email,
                    full_name=user.full_name,
                    username=user.username,
                    password=data.password,
                    role=user.role,
                    county=user.county,
                )
            except Exception as e:
                print(f"[EMAIL WARNING] Welcome email failed for {user.email}: {e}")

    return user


# ── Authentication ────────────────────────────────────────────────────────────

def authenticate_user(db: Session, identifier: str, password: str) -> User:
    """
    Authenticate by username OR email.
    Uses identical error message and timing regardless of failure reason
    to prevent user enumeration attacks.
    """
    identifier = identifier.strip().lower()

    # Check rate limit first
    _check_rate_limit(identifier)

    # Look up by username or email
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    # Always call verify_password (even if user not found) to ensure constant
    # response time and prevent timing-based enumeration.
    # _DUMMY_HASH is a valid bcrypt hash — passlib will process it without warnings.
    password_ok = verify_password(password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok or not user.is_active:
        _record_failed_attempt(identifier)
        # Generic message — don't reveal whether username or password was wrong
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your username and password.",
        )

    _clear_attempts(identifier)
    return user


def login_user(db: Session, username: str, password: str) -> dict:
    user = authenticate_user(db, username, password)
    token = create_access_token({
        "sub":    user.id,
        "role":   user.role,
        "county": user.county,
    })
    return {
        "token":        token,
        "role":         user.role,
        "county":       user.county,
        "username":     user.username,
        "full_name":    user.full_name,
        "staff_number": user.staff_number,
    }


# ── Admin actions ─────────────────────────────────────────────────────────────

def deactivate_user(db: Session, user_id: str, requesting_user: User) -> User:
    if requesting_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(status_code=403, detail="Only system admins can deactivate accounts.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == requesting_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active = False
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session) -> list[User]:
    return db.query(User).order_by(User.created_at.desc()).all()