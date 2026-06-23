import uuid
from datetime import date
from sqlalchemy import func
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.models.trainer import SessionTrainer
from app.models.user import User
from app.lib.county import normalize_county
from app.schemas.session import SessionCreate, SessionUpdate, TrainingReportSchema, SessionOut

_APPROVAL_SENSITIVE_FIELDS = {"county", "facility", "start_date", "end_date"}
_SESSION_LOAD_OPTIONS = (
    selectinload(TrainingSession.participants),
    selectinload(TrainingSession.trainers),
)


def _session_query(db: Session):
    return db.query(TrainingSession).options(*_SESSION_LOAD_OPTIONS)


def to_session_out(db: Session, session: TrainingSession, reviewer_map: dict[str, str] | None = None) -> SessionOut:
    out = SessionOut.model_validate(session)
    if session.approved_by:
        if reviewer_map is not None:
            name = reviewer_map.get(session.approved_by)
        else:
            reviewer = db.query(User.full_name).filter(User.id == session.approved_by).scalar()
            name = reviewer
        if name:
            out = out.model_copy(update={"approved_by_name": name})
    return out


def get_all_sessions(
    db: Session, county: str | None = None, skip: int = 0, limit: int = 100
) -> list[SessionOut]:
    q = _session_query(db)
    if county:
        q = q.filter(TrainingSession.county == county)
    sessions = q.order_by(TrainingSession.created_at.desc()).offset(skip).limit(limit).all()

    # Batch-load all reviewer names in one query instead of one query per session
    reviewer_ids = {s.approved_by for s in sessions if s.approved_by}
    reviewer_map: dict[str, str] = {}
    if reviewer_ids:
        rows = db.query(User.id, User.full_name).filter(User.id.in_(reviewer_ids)).all()
        reviewer_map = {r.id: r.full_name for r in rows}

    return [to_session_out(db, s, reviewer_map) for s in sessions]


def get_session_or_404(db: Session, session_id: str) -> TrainingSession:
    s = _session_query(db).filter(TrainingSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return s


def get_session_out_or_404(db: Session, session_id: str) -> SessionOut:
    return to_session_out(db, get_session_or_404(db, session_id))


def create_session(db: Session, data: SessionCreate, created_by: str) -> SessionOut:
    s = TrainingSession(
        id=str(uuid.uuid4()),
        title=data.title,
        county=normalize_county(data.county),
        facility=data.facility,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        created_by=created_by,
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return to_session_out(db, s)


def update_session(db: Session, session: TrainingSession, data: SessionUpdate) -> SessionOut:
    if session.certificates_issued:
        raise HTTPException(
            status_code=400,
            detail="Cannot edit a session after certificates have been issued.",
        )

    updates = data.model_dump(exclude_none=True)

    new_start = updates.get("start_date", session.start_date)
    new_end   = updates.get("end_date",   session.end_date)
    if new_start and new_end and new_start > new_end:
        raise HTTPException(status_code=400, detail="start_date must be before or equal to end_date.")

    for field, value in updates.items():
        if field == "county" and value is not None:
            value = normalize_county(value)
        setattr(session, field, value)

    material_change = bool(updates.keys() & _APPROVAL_SENSITIVE_FIELDS)
    if material_change and session.approval_status == "APPROVED" and not session.certificates_issued:
        session.approval_status = "PENDING"
        session.approval_note = None

    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def delete_session(db: Session, session: TrainingSession) -> None:
    if session.certificates_issued:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session after certificates have been issued.",
        )
    db.delete(session)
    db.commit()


def approve_session(db: Session, session: TrainingSession, reviewed_by: str) -> SessionOut:
    if session.approval_status == "APPROVED":
        raise HTTPException(status_code=400, detail="Session is already approved.")
    session.approval_status = "APPROVED"
    session.approved_by     = reviewed_by
    session.approval_note   = None
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def reject_session(db: Session, session: TrainingSession, note: str, reviewed_by: str) -> SessionOut:
    if session.approval_status == "REJECTED":
        raise HTTPException(status_code=400, detail="Session is already rejected.")
    if session.approval_status == "APPROVED" and len(session.participants) > 0:
        raise HTTPException(
            status_code=400,
            detail="Cannot reject an approved session that already has registered participants.",
        )
    session.approval_status = "REJECTED"
    session.approval_note   = note
    session.approved_by     = reviewed_by
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def submit_report(db: Session, session: TrainingSession, report: TrainingReportSchema) -> SessionOut:
    if session.approval_status != "APPROVED":
        raise HTTPException(
            status_code=400,
            detail="Session must be approved before submitting a report.",
        )
    if session.certificates_issued:
        raise HTTPException(status_code=400, detail="Cannot submit a report after certificates have been issued.")
    if session.report_approval_status == "APPROVED":
        raise HTTPException(status_code=400, detail="Report is already approved and cannot be resubmitted.")
    if session.report_approval_status == "PENDING" and session.report_submitted_at:
        raise HTTPException(status_code=400, detail="Report is awaiting approval and cannot be modified.")
    session.report_summary         = report.summary
    session.report_challenges      = report.challenges
    session.report_recommendations = report.recommendations
    session.report_submitted_at    = date.today()
    session.report_approval_status = "PENDING"
    session.report_approval_note   = None
    session.status                 = "COMPLETED"
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def approve_report(db: Session, session: TrainingSession) -> SessionOut:
    if not session.report_submitted_at:
        raise HTTPException(status_code=400, detail="No report has been submitted for this session.")
    if session.report_approval_status == "APPROVED":
        raise HTTPException(status_code=400, detail="Report is already approved.")
    session.report_approval_status = "APPROVED"
    session.report_approval_note   = None
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def reject_report(db: Session, session: TrainingSession, note: str) -> SessionOut:
    if session.report_approval_status == "REJECTED":
        raise HTTPException(status_code=400, detail="Report is already rejected.")
    session.report_approval_status = "REJECTED"
    session.report_approval_note   = note
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


# ── Participants ───────────────────────────────────────────────────────────────

def _sync_trainee_count(db: Session, s: TrainingSession) -> None:
    s.trainee_count = db.query(func.count(Participant.id)).filter(
        Participant.session_id == s.id
    ).scalar() or 0


def add_participant(
    db: Session,
    session: TrainingSession,
    name: str,
    cadre: str,
    facility: str,
    status: str = "PRESENT",
    staff_number: str | None = None,
) -> Participant:
    p = Participant(
        id=str(uuid.uuid4()),
        session_id=session.id,
        name=name,
        cadre=cadre,
        facility=facility,
        status=status,
        staff_number=staff_number,
    )
    db.add(p)
    db.flush()
    _sync_trainee_count(db, session)
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
    pre: float | None,
    post: float | None,
) -> Participant:
    if pre is not None and not (0 <= pre <= 100):
        raise HTTPException(status_code=400, detail="pre_test_score must be between 0 and 100.")
    if post is not None and not (0 <= post <= 100):
        raise HTTPException(status_code=400, detail="post_test_score must be between 0 and 100.")
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    if pre is not None:
        p.pre_test_score = pre
    if post is not None:
        p.post_test_score = post
    db.commit()
    db.refresh(p)
    return p


def remove_participant(db: Session, session: TrainingSession, participant_id: str) -> None:
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    db.delete(p)
    db.flush()
    _sync_trainee_count(db, session)
    db.commit()


# ── Trainers ───────────────────────────────────────────────────────────────────

def add_trainer(db: Session, session: TrainingSession, name: str, cadre: str, phone: str) -> SessionTrainer:
    t = SessionTrainer(
        id=str(uuid.uuid4()),
        session_id=session.id,
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
