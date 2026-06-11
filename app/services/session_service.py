import uuid
from datetime import date, datetime
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.models.trainer import SessionTrainer
from app.schemas.session import SessionCreate, SessionUpdate, TrainingReportSchema

# Fields that materially change the session and require re-approval.
# Cosmetic/admin edits (e.g. fixing a typo in the title) do NOT reset approval.
_APPROVAL_SENSITIVE_FIELDS = {"county", "facility", "start_date", "end_date"}


def get_all_sessions(db: Session, county: str | None = None) -> list[TrainingSession]:
    q = db.query(TrainingSession)
    if county:
        q = q.filter(TrainingSession.county == county)
    return q.order_by(TrainingSession.created_at.desc()).all()


def get_session_or_404(db: Session, session_id: str) -> TrainingSession:
    s = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return s


def create_session(db: Session, data: SessionCreate, created_by: str) -> TrainingSession:
    # Validate date range on creation
    _validate_date_range(data.start_date, data.end_date)

    s = TrainingSession(
        id=str(uuid.uuid4()),
        title=data.title,
        county=data.county,
        facility=data.facility,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        created_by=created_by,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


def _validate_date_range(start_date: str, end_date: str) -> None:
    """
    Validate that start_date <= end_date.
    Raises HTTPException directly — kept outside the try/except
    so it is never accidentally swallowed by a ValueError catch.
    """
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt   = datetime.strptime(end_date,   "%Y-%m-%d")
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Dates must be in YYYY-MM-DD format.",
        )

    # This check is outside the except block so the HTTPException
    # is never caught by the ValueError handler above.
    if start_dt > end_dt:
        raise HTTPException(
            status_code=400,
            detail="start_date must be before or equal to end_date.",
        )


def update_session(db: Session, session_id: str, data: SessionUpdate) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    if s.certificates_issued:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a session after certificates have been issued.",
        )

    updates = data.model_dump(exclude_none=True)

    # Validate date range if either date is changing
    new_start = updates.get("start_date", s.start_date)
    new_end   = updates.get("end_date",   s.end_date)
    if new_start and new_end:
        _validate_date_range(new_start, new_end)

    # Apply all the changes
    for field, value in updates.items():
        setattr(s, field, value)

    # Only reset approval to PENDING if a material field changed AND the session
    # was already approved (but certs haven't been issued yet).
    # This prevents a typo fix in the title from forcing a full re-approval cycle.
    material_change = bool(updates.keys() & _APPROVAL_SENSITIVE_FIELDS)
    if material_change and s.approval_status == "APPROVED" and not s.certificates_issued:
        s.approval_status = "PENDING"
        s.approval_note = None

    db.commit()
    db.refresh(s)
    return s


def delete_session(db: Session, session_id: str) -> None:
    s = get_session_or_404(db, session_id)
    db.delete(s)
    db.commit()


def approve_session(db: Session, session_id: str, approved_by: str) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    s.approval_status = "APPROVED"
    s.approved_by = approved_by
    s.approval_note = None
    db.commit()
    db.refresh(s)
    return s


def reject_session(db: Session, session_id: str, note: str, approved_by: str) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    s.approval_status = "REJECTED"
    s.approval_note = note
    s.approved_by = approved_by
    db.commit()
    db.refresh(s)
    return s


def submit_report(db: Session, session_id: str, report: TrainingReportSchema) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    if s.approval_status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Session must be approved before submitting a report.",
        )
    s.report_summary         = report.summary
    s.report_challenges      = report.challenges
    s.report_recommendations = report.recommendations
    s.report_submitted_at    = str(date.today())
    s.report_approval_status = "PENDING"
    s.report_approval_note   = None
    s.status                 = "COMPLETED"
    db.commit()
    db.refresh(s)
    return s


def approve_report(db: Session, session_id: str) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    s.report_approval_status = "APPROVED"
    s.report_approval_note   = None
    db.commit()
    db.refresh(s)
    return s


def reject_report(db: Session, session_id: str, note: str) -> TrainingSession:
    s = get_session_or_404(db, session_id)
    s.report_approval_status = "REJECTED"
    s.report_approval_note   = note
    db.commit()
    db.refresh(s)
    return s


# ── Participants ───────────────────────────────────────────────────────────────

def add_participant(
    db: Session,
    session_id: str,
    name: str,
    cadre: str,
    facility: str,
    status: str = "PRESENT",
    staff_number: str | None = None,
) -> Participant:
    s = get_session_or_404(db, session_id)
    p = Participant(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=name,
        cadre=cadre,
        facility=facility,
        status=status,
        staff_number=staff_number,
    )
    db.add(p)
    s.trainee_count = (s.trainee_count or 0) + 1
    db.commit()
    db.refresh(p)
    return p


def toggle_attendance(db: Session, session_id: str, participant_id: str) -> Participant:
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    p.status = "ABSENT" if p.status == "PRESENT" else "PRESENT"
    db.commit()
    db.refresh(p)
    return p


def update_scores(
    db: Session,
    session_id: str,
    participant_id: str,
    pre: float,
    post: float,
) -> Participant:
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    p.pre_test_score  = pre
    p.post_test_score = post
    db.commit()
    db.refresh(p)
    return p


def remove_participant(db: Session, session_id: str, participant_id: str) -> None:
    s = get_session_or_404(db, session_id)
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    db.delete(p)
    s.trainee_count = max(0, (s.trainee_count or 1) - 1)
    db.commit()


# ── Trainers ───────────────────────────────────────────────────────────────────

def add_trainer(db: Session, session_id: str, name: str, cadre: str, phone: str) -> SessionTrainer:
    get_session_or_404(db, session_id)
    t = SessionTrainer(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=name,
        cadre=cadre,
        phone=phone,
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return t


def remove_trainer(db: Session, session_id: str, trainer_id: str) -> None:
    t = db.query(SessionTrainer).filter(
        SessionTrainer.id == trainer_id,
        SessionTrainer.session_id == session_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    db.delete(t)
    db.commit()