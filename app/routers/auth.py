from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Query, Response, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserCreate, UserOut
from app.schemas.common import PaginatedResponse
from app.core.dependencies import get_current_user, require_system_admin
from app.core.security import verify_password
from app.core.rate_limit import check_login_ip_rate_limit, check_forgot_password_rate_limit
from app.models.user import User
from app.services.auth_service import (
    login_user, create_user, deactivate_user, activate_user,
    list_users, complete_setup, request_password_reset,
    change_user_password, clear_auth_cookie,
)

router = APIRouter(prefix="/auth", tags=["Auth"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class SetupPasswordRequest(BaseModel):
    token: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    identifier: str  # username or email


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, response: Response, request: Request, db: Session = Depends(get_db)):
    from app.core.config import settings
    # IP throttle always in production; also when RATE_LIMIT_STORAGE=database locally
    if settings.is_production or settings.rate_limit_use_database:
        check_login_ip_rate_limit(request, db=db)
    return login_user(db, data.username, data.password, response)


@router.post("/logout", status_code=200)
def logout(response: Response):
    clear_auth_cookie(response)
    return {"message": "Logged out successfully."}


@router.post("/setup-password", response_model=LoginResponse)
def setup_password(data: SetupPasswordRequest, response: Response, db: Session = Depends(get_db)):
    return complete_setup(db, data.token, data.new_password, response)


@router.post("/forgot-password", status_code=200)
def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    check_forgot_password_rate_limit(request, db=db)
    return request_password_reset(db, data.identifier, background_tasks)


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return create_user(db, data, background_tasks, requesting_user_id=current_user.id)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=200)
def change_password(
    data: ChangePasswordRequest,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    change_user_password(db, current_user, data.new_password)
    clear_auth_cookie(response)
    return {"message": "Password updated successfully. Please log in again."}


@router.get("/users", response_model=PaginatedResponse[UserOut])
def get_all_users(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_system_admin),
):
    items, total = list_users(db, skip, limit)
    return PaginatedResponse(items=items, total=total, skip=skip, limit=limit)


@router.patch("/users/{user_id}/deactivate", response_model=UserOut)
def deactivate(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return deactivate_user(db, user_id, current_user)


@router.patch("/users/{user_id}/activate", response_model=UserOut)
def activate(
    user_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_system_admin),
):
    return activate_user(db, user_id, requesting_user_id=current_user.id)
