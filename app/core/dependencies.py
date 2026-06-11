from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session

from app.core.security import decode_token
from app.database import get_db
from app.models.user import User

bearer_scheme = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials
    try:
        payload = decode_token(token)
        user_id: str = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired or invalid")

    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or account deactivated")
    return user


def require_roles(*roles: str):
    """Role guard factory — use as a FastAPI dependency."""
    def checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' is not authorised for this action.",
            )
        return current_user
    return checker


# ── Pre-built role guards ──────────────────────────────────────────────────────

# ROLE_SYSTEM_ADMIN is included in require_trainer so that system admins
# can also create, edit, and delete sessions (full operational access).
require_trainer        = require_roles("ROLE_TRAINER", "ROLE_SYSTEM_ADMIN")

require_county_officer = require_roles("ROLE_COUNTY_OFFICER", "ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_national_admin = require_roles("ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_me_manager     = require_roles("ROLE_ME_MANAGER", "ROLE_NATIONAL_ADMIN", "ROLE_SYSTEM_ADMIN")
require_system_admin   = require_roles("ROLE_SYSTEM_ADMIN")
require_any_staff      = require_roles(
    "ROLE_TRAINER", "ROLE_COUNTY_OFFICER",
    "ROLE_NATIONAL_ADMIN", "ROLE_ME_MANAGER", "ROLE_SYSTEM_ADMIN",
)