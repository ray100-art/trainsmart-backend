"""TOTP multi-factor authentication for privileged TrainSMART accounts."""
from __future__ import annotations

from datetime import timedelta

import pyotp
from fastapi import HTTPException, status
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import create_access_token, decode_token, verify_password
from app.models.user import User
from app.services.audit_service import log_action

MFA_PURPOSE = "mfa_challenge"
ISSUER = "TrainSMART"


def role_requires_mfa(role: str) -> bool:
    if not settings.MFA_ENABLED or not settings.MFA_ENFORCE_PRIVILEGED:
        return False
    return role in settings.mfa_required_roles_set


def assert_mfa_available() -> None:
    if not settings.MFA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Multi-factor authentication is temporarily disabled.",
        )


def create_mfa_challenge_token(user: User) -> str:
    return create_access_token(
        {
            "sub": user.id,
            "purpose": MFA_PURPOSE,
            "tv": user.token_version or 0,
        },
        expires_delta=timedelta(minutes=settings.MFA_CHALLENGE_MINUTES),
    )


def resolve_mfa_user(db: Session, mfa_token: str) -> User:
    try:
        payload = decode_token(mfa_token)
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="MFA challenge expired. Please sign in again.",
        )
    if payload.get("purpose") != MFA_PURPOSE:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token.")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid MFA token.")
    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found.")
    if (user.token_version or 0) != payload.get("tv", 0):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired. Please sign in again.",
        )
    return user


def verify_totp(secret: str, code: str) -> bool:
    cleaned = (code or "").strip().replace(" ", "")
    if not cleaned.isdigit() or len(cleaned) != 6:
        return False
    totp = pyotp.TOTP(secret)
    return bool(totp.verify(cleaned, valid_window=1))


def begin_setup(user: User) -> dict:
    """Generate a new secret (not persisted until confirm)."""
    secret = pyotp.random_base32()
    totp = pyotp.TOTP(secret)
    uri = totp.provisioning_uri(name=user.email or user.username, issuer_name=ISSUER)
    return {"secret": secret, "otpauth_uri": uri}


def confirm_setup(
    db: Session,
    user: User,
    secret: str,
    code: str,
    *,
    ip_address: str | None = None,
) -> None:
    if not secret or len(secret) < 16:
        raise HTTPException(status_code=400, detail="Invalid MFA secret.")
    if not verify_totp(secret, code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code. Try again.")
    user.mfa_secret = secret
    user.mfa_enabled = True
    log_action(
        db,
        user_id=user.id,
        action="MFA_ENABLE",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
    db.refresh(user)


def disable_mfa(
    db: Session,
    user: User,
    password: str,
    code: str,
    *,
    ip_address: str | None = None,
) -> None:
    if role_requires_mfa(user.role):
        raise HTTPException(
            status_code=400,
            detail="MFA cannot be disabled for this privileged role.",
        )
    if not verify_password(password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect.")
    if not user.mfa_enabled or not user.mfa_secret:
        raise HTTPException(status_code=400, detail="MFA is not enabled.")
    if not verify_totp(user.mfa_secret, code):
        raise HTTPException(status_code=400, detail="Invalid authenticator code.")
    user.mfa_enabled = False
    user.mfa_secret = None
    user.token_version = (user.token_version or 0) + 1
    log_action(
        db,
        user_id=user.id,
        action="MFA_DISABLE",
        entity_type="user",
        entity_id=user.id,
        ip_address=ip_address,
    )
    db.commit()
