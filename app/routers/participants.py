from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.participant import ParticipantCreate, ParticipantOut
from app.schemas.participant import ScoresUpdate
from app.services import session_service
from app.services.participant_import_service import bulk_import_participants_csv, participant_csv_template
from app.lib.uploads import read_upload_text
from app.core.dependencies import (
    require_trainer, require_any_staff,
    assert_owns_session, assert_session_approved, assert_training_mutable,
    assert_can_view_session,
)
from app.models.user import User

router = APIRouter(prefix="/sessions/{session_id}/participants", tags=["Participants"])


@router.get("", response_model=list[ParticipantOut])
def list_participants(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_any_staff),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_can_view_session(s, current_user)
    return s.participants


@router.get("/import/template.csv")
def participant_import_template(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    return PlainTextResponse(
        content=participant_csv_template(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="participants-template.csv"'},
    )


@router.post("/import")
def import_participants_csv(
    session_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)

    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="Upload a .csv file.")

    text = read_upload_text(file)
    return bulk_import_participants_csv(db, s, text, added_by=current_user.id)


@router.post("", response_model=ParticipantOut, status_code=201)
def add_participant(
    session_id: str,
    data: ParticipantCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    return session_service.add_participant(
        db, s, data.name, data.cadre, data.facility, data.status, data.staff_number,
        added_by=current_user.id,
    )


@router.patch("/{participant_id}/attendance", response_model=ParticipantOut)
def toggle_attendance(
    session_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    return session_service.toggle_attendance(db, session_id, participant_id, toggled_by=current_user.id)


@router.patch("/{participant_id}/scores", response_model=ParticipantOut)
def update_scores(
    session_id: str,
    participant_id: str,
    data: ScoresUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    return session_service.update_scores(
        db, session_id, participant_id, data.pre_test_score, data.post_test_score,
        updated_by=current_user.id,
    )


@router.delete("/{participant_id}", status_code=204)
def remove_participant(
    session_id: str,
    participant_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_trainer),
):
    s = session_service.get_session_or_404(db, session_id)
    assert_owns_session(s, current_user)
    assert_session_approved(s)
    assert_training_mutable(s)
    session_service.remove_participant(db, s, participant_id, removed_by=current_user.id)
