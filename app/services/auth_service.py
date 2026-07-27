import uuid
import secrets
import logging
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor

from sqlalchemy.orm import Session
from fastapi import BackgroundTasks, HTTPException, status, Response

from app.models.user import User
from app.schemas.auth import UserCreate
from app.core.security import hash_password, verify_password, create_access_token
from app.core.config import settings
from app.core.rate_limit import (
    check_account_lockout, record_failed_login, clear_failed_logins,
)
from app.lib.county import normalize_county
from app.services.email_service import send_welcome_email
from app.services.audit_service import log_action

logger = logging.getLogger(__name__)

# Offload SMTP so Uvicorn workers are not blocked after the response is sent
_email_executor = ThreadPoolExecutor(max_workers=2, thread_name_prefix="email")

VALID_ROLES = {
    "ROLE_TRAINER",
    "ROLE_COUNTY_OFFICER",
    "ROLE_NATIONAL_ADMIN",
    "ROLE_ME_MANAGER",
    "ROLE_SYSTEM_ADMIN",
    "ROLE_TRAINEE",
}

_DUMMY_HASH = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TsuQSm0l8AKKqFvpNP1M0SnbLpqu"

SETUP_TOKEN_HOURS = 48


def validate_password_strength(password: str) -> None:
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


def _issue_setup_token() -> tuple[str, datetime]:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(hours=SETUP_TOKEN_HOURS)
    return token, expires


def _set_auth_cookie(response: Response, token: str) -> None:
    max_age = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    response.set_cookie(
        key=settings.COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite_effective,
        max_age=max_age,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(
        key=settings.COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite_effective,
    )


def _build_token(user: User) -> str:
    return create_access_token({
        "sub": user.id,
        "role": user.role,
        "county": user.county,
        "tv": user.token_version,
    })


def _auth_response_body(user: User) -> dict:
    """Browser clients use the httpOnly cookie; JWT is not returned in the body."""
    return {
        "role":         user.role,
        "county":       user.county,
        "username":     user.username,
        "full_name":    user.full_name,
        "staff_number": user.staff_number,
    }


def create_user(
    db: Session,
    data: UserCreate,
    background_tasks: BackgroundTasks | None = None,
    requesting_user_id: str | None = None,
) -> User:
    validate_password_strength(data.password)
    _validate_role(data.role)

    existing = db.query(User).filter(
        (User.username == data.username) | (User.email == data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with that username or email already exists.",
        )

    setup_token, setup_expires = _issue_setup_token()

    user = User(
        id=str(uuid.uuid4()),
        username=data.username.strip().lower(),
        email=data.email.strip().lower(),
        hashed_password=hash_password(data.password),
        full_name=data.full_name.strip(),
        role=data.role,
        county=normalize_county(data.county),
        staff_number=data.staff_number,
        setup_token=setup_token,
        setup_token_expires=setup_expires,
    )
    db.add(user)
    db.flush()
    log_action(db, user_id=requesting_user_id, action="CREATE_USER",
               entity_type="user", entity_id=user.id,
               detail=f"{user.username} ({user.role}, {user.county})")
    db.commit()
    db.refresh(user)

    if settings.EMAIL_ENABLED and user.email:
        setup_url = f"{settings.FRONTEND_URL}/setup-password?token={setup_token}"

        def _send():
            send_welcome_email(
                to_email=user.email,
                full_name=user.full_name,
                username=user.username,
                setup_url=setup_url,
                role=user.role,
                county=user.county,
            )

        if background_tasks is not None:
            _email_executor.submit(_send)
        else:
            try:
                _send()
            except Exception as exc:
                logger.warning("Welcome email failed for %s: %s", user.email, exc)

    return user


def authenticate_user(db: Session, identifier: str, password: str) -> User:
    identifier = identifier.strip().lower()
    check_account_lockout(db, identifier)

    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()

    password_ok = verify_password(password, user.hashed_password if user else _DUMMY_HASH)

    if not user or not password_ok or not user.is_active:
        record_failed_login(db, identifier)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials. Please check your username and password.",
        )

    clear_failed_logins(db, identifier)
    return user


def login_user(db: Session, username: str, password: str, response: Response) -> dict:
    user = authenticate_user(db, username, password)
    token = _build_token(user)
    _set_auth_cookie(response, token)
    log_action(db, user_id=user.id, action="LOGIN",
               entity_type="user", entity_id=user.id)
    db.commit()
    return _auth_response_body(user)


def complete_setup(db: Session, token: str, new_password: str, response: Response) -> dict:
    validate_password_strength(new_password)
    user = db.query(User).filter(User.setup_token == token).first()
    if not user:
        raise HTTPException(status_code=400, detail="Invalid or expired setup link.")
    if user.setup_token_expires:
        expires = user.setup_token_expires
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) > expires:
            raise HTTPException(status_code=400, detail="Setup link has expired. Contact your administrator.")

    user.hashed_password      = hash_password(new_password)
    user.setup_token          = None
    user.setup_token_expires  = None
    user.token_version        = (user.token_version or 0) + 1
    log_action(db, user_id=user.id, action="SETUP_PASSWORD",
               entity_type="user", entity_id=user.id)
    db.commit()
    db.refresh(user)

    jwt_token = _build_token(user)
    _set_auth_cookie(response, jwt_token)
    return _auth_response_body(user)


def change_user_password(db: Session, user: User, new_password: str) -> None:
    validate_password_strength(new_password)
    if verify_password(new_password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )
    user.hashed_password     = hash_password(new_password)
    user.token_version       = (user.token_version or 0) + 1
    user.setup_token         = None
    user.setup_token_expires = None
    log_action(db, user_id=user.id, action="CHANGE_PASSWORD",
               entity_type="user", entity_id=user.id)
    db.commit()


def deactivate_user(db: Session, user_id: str, requesting_user: User) -> User:
    if requesting_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(status_code=403, detail="Only system admins can deactivate accounts.")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == requesting_user.id:
        raise HTTPException(status_code=400, detail="You cannot deactivate your own account.")
    user.is_active     = False
    user.token_version = (user.token_version or 0) + 1
    log_action(db, user_id=requesting_user.id, action="DEACTIVATE_USER",
               entity_type="user", entity_id=user.id,
               detail=user.username)
    db.commit()
    db.refresh(user)
    return user


def activate_user(db: Session, user_id: str, requesting_user_id: str | None = None) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    log_action(db, user_id=requesting_user_id, action="ACTIVATE_USER",
               entity_type="user", entity_id=user.id,
               detail=user.username)
    db.commit()
    db.refresh(user)
    return user


def list_users(db: Session, skip: int = 0, limit: int = 100) -> tuple[list[User], int]:
    q = db.query(User)
    total = q.count()
    items = q.order_by(User.created_at.desc()).offset(skip).limit(limit).all()
    return items, total
