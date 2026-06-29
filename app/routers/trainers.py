from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.trainer import TrainerCreate, TrainerOut
from app.services import session_service
from app.core.dependencies import require_trainer, assert_owns_session, assert_session_approved, assert_training_mutable
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
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    return session_service.add_trainer(db, s, data.name, data.cadre, data.phone, added_by=current_user.id)


@router.delete("/{trainer_id}", status_code=204)
def remove_trainer(
    session_id: str,
    trainer_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    session_service.remove_trainer(db, session_id, trainer_id, removed_by=current_user.id)
