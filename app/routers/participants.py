from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.participant import ParticipantCreate, ParticipantOut, ScoresUpdate
from app.services import session_service
from app.core.dependencies import require_trainer, require_any_staff
from app.models.user import User

router = APIRouter(prefix="/sessions/{session_id}/participants", tags=["Participants"])


@router.get("", response_model=list[ParticipantOut])
def list_participants(
    session_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_staff),
):
    s = session_service.get_session_or_404(db, session_id)
    return s.participants


@router.post("", response_model=ParticipantOut, status_code=201)
def add_participant(
    session_id: str,
    data: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its participants.",
        )
    return session_service.add_participant(
        db, session_id, data.name, data.cadre, data.facility, data.status, data.staff_number
    )


@router.patch("/{participant_id}/attendance", response_model=ParticipantOut)
def toggle_attendance(
    session_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its participants.",
        )
    return session_service.toggle_attendance(db, session_id, participant_id)


@router.patch("/{participant_id}/scores", response_model=ParticipantOut)
def update_scores(
    session_id: str,
    participant_id: str,
    data: ScoresUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its participants.",
        )
    return session_service.update_scores(
        db, session_id, participant_id, data.pre_test_score, data.post_test_score
    )


@router.delete("/{participant_id}", status_code=204)
def remove_participant(
    session_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    if s.created_by != current_user.id and current_user.role != "ROLE_SYSTEM_ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not own this session and cannot modify its participants.",
        )
    session_service.remove_participant(db, session_id, participant_id)