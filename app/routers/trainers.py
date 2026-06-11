from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.trainer import TrainerCreate, TrainerOut
from app.services import session_service
from app.core.dependencies import require_trainer
from app.models.user import User

router = APIRouter(prefix="/sessions/{session_id}/trainers", tags=["Trainers"])


@router.post("", response_model=TrainerOut, status_code=201)
def add_trainer(
    session_id: str,
    data: TrainerCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its trainers.",
        )
    return session_service.add_trainer(db, session_id, data.name, data.cadre, data.phone)


@router.delete("/{trainer_id}", status_code=204)
def remove_trainer(
    session_id: str,
    trainer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its trainers.",
        )
    session_service.remove_trainer(db, session_id, trainer_id)