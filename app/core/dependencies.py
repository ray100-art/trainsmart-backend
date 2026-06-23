from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jwt.exceptions import InvalidTokenError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.core.config import settings
from app.database import get_db
from app.models.user import User
from app.lib.county import normalize_county

bearer_scheme = HTTPBearer(auto_error=False)

_NATIONAL_ROLES = frozenset({"ROLE_NATIONAL_ADMIN", "ROLE_ME_MANAGER", "ROLE_SYSTEM_ADMIN"})


def _extract_token(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None,
) -> str | None:
    if credentials and credentials.credentials:
        return credentials.credentials
    return request.cookies.get(settings.COOKIE_NAME)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = _extract_token(request, credentials)
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    try:
        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        token_version = payload.get("tv", 0)
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except InvalidTokenError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    user = db.query(User).filter(User.id == user_id, User.is_active.is_(True)).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or account deactivated")

    if (user.token_version or 0) != token_version:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired. Please log in again.")

    return user


def require_roles(*roles: str):
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorised for this action.",
            )
        return current_user
    return checker


def assert_owns_session(session, current_user: User) -> None:
    if session.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session.",
        )


def assert_county_access(session, current_user: User) -> None:
    if current_user.role == "ROLE_COUNTY_OFFICER":
        if normalize_county(session.county) != normalize_county(current_user.county):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"You are not authorised to manage sessions in {session.county}.",
            )


def assert_can_view_session(session, current_user: User) -> None:
    """Restrict session reads by role and county."""
    if current_user.role in _NATIONAL_ROLES:
        return
    if current_user.role == "ROLE_COUNTY_OFFICER":
        if normalize_county(session.county) != normalize_county(current_user.county):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this session.")
        return
    if current_user.role == "ROLE_TRAINER":
        if session.created_by != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this session.")
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You cannot view this session.")


def assert_trainer_county(session_county: str, current_user: User) -> None:
    if current_user.role == "ROLE_TRAINER":
        if normalize_county(session_county) != normalize_county(current_user.county):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Trainers may only create sessions in their own county ({current_user.county}).",
            )


def resolve_list_county(current_user: User, county: str | None) -> str | None:
    if current_user.role == "ROLE_COUNTY_OFFICER":
        return normalize_county(current_user.county)
    if current_user.role == "ROLE_TRAINER":
        return normalize_county(current_user.county)
    return normalize_county(county) if county else None


def assert_session_approved(session) -> None:
    if session.approval_status != "APPROVED":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Session must be approved before managing participants or trainers.",
        )


def assert_training_mutable(session) -> None:
    if session.certificates_issued:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot modify training data after certificates have been issued.",
        )


require_trainer        = require_roles("ROLE_TRAINER", "ROLE_SYSTEM_ADMIN")
require_county_officer = require_roles("ROLE_COUNTY_OFFICER", "ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_national_admin = require_roles("ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_me_manager     = require_roles("ROLE_ME_MANAGER", "ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_system_admin   = require_roles("ROLE_SYSTEM_ADMIN")
require_any_staff      = require_roles(
    "ROLE_TRAINER", "ROLE_COUNTY_OFFICER",
    "ROLE_NATIONAL_ADMIN", "ROLE_ME_MANAGER", "ROLE_SYSTEM_ADMIN",
)
