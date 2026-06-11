from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, UserCreate, UserOut
from app.services.auth_service import login_user, create_user, deactivate_user, list_users
from app.core.dependencies import get_current_user, require_system_admin
from app.core.security import verify_password, hash_password
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Auth"])


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/login", response_model=LoginResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    return login_user(db, data.username, data.password)


@router.post("/register", response_model=UserOut, status_code=201)
def register(
    data: UserCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: User = Depends(require_system_admin),
):
    return create_user(db, data, background_tasks)


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.post("/change-password", status_code=200)
def change_password(
    data: ChangePasswordRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify current password
    if not verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect.",
        )
    # Enforce same strength rules as registration
    from app.services.auth_service import _validate_password_strength
    _validate_password_strength(data.new_password)

    # Prevent reuse of the same password
    if verify_password(data.new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be different from your current password.",
        )

    current_user.hashed_password = hash_password(data.new_password)
    db.commit()
    return {"message": "Password updated successfully."}


@router.get("/users", response_model=list[UserOut])
def get_all_users(
    db: Session = Depends(get_db),
    _: User = Depends(require_system_admin),
):
    return list_users(db)


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
    _: User = Depends(require_system_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    user.is_active = True
    db.commit()
    db.refresh(user)
    return user