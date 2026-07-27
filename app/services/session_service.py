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
from app.schemas.session import SessionCreate, SessionUpdate, TrainingReportSchema, SessionOut, SessionSummary
from app.models.training_program import TrainingProgram
from app.services.program_service import get_program_or_404
from app.services.audit_service import log_action

_APPROVAL_SENSITIVE_FIELDS = {"county", "facility", "start_date", "end_date"}
_SESSION_DETAIL_OPTIONS = (
    selectinload(TrainingSession.participants),
    selectinload(TrainingSession.trainers),
    selectinload(TrainingSession.program),
    selectinload(TrainingSession.sponsor),
)

_SESSION_LIST_OPTIONS = (
    selectinload(TrainingSession.program),
    selectinload(TrainingSession.sponsor),
)


def _session_query(db: Session):
    return db.query(TrainingSession).options(*_SESSION_DETAIL_OPTIONS)


def _session_list_query(db: Session):
    return db.query(TrainingSession).options(*_SESSION_LIST_OPTIONS)


def to_session_out(db: Session, session: TrainingSession, reviewer_map: dict[str, str] | None = None) -> SessionOut:
    out = SessionOut.model_validate(session)

    # Resolve session approver name
    if session.approved_by:
        if reviewer_map is not None:
            name = reviewer_map.get(session.approved_by)
        else:
            name = db.query(User.full_name).filter(User.id == session.approved_by).scalar()
        if name:
            out = out.model_copy(update={"approved_by_name": name})

    # Resolve report approver name
    if session.report_approved_by:
        if reviewer_map is not None:
            rname = reviewer_map.get(session.report_approved_by)
        else:
            rname = db.query(User.full_name).filter(User.id == session.report_approved_by).scalar()
        if rname:
            out = out.model_copy(update={"report_approved_by_name": rname})

    if session.program:
        out = out.model_copy(update={
            "program_code": session.program.code,
            "program_name": session.program.name,
        })

    if session.sponsor:
        out = out.model_copy(update={"sponsor_name": session.sponsor.name})

    return out


def to_session_summary(
    db: Session, session: TrainingSession, reviewer_map: dict[str, str] | None = None
) -> SessionSummary:
    out = SessionSummary.model_validate(session)

    if session.approved_by:
        name = (reviewer_map or {}).get(session.approved_by) if reviewer_map is not None else None
        if name is None:
            name = db.query(User.full_name).filter(User.id == session.approved_by).scalar()
        if name:
            out = out.model_copy(update={"approved_by_name": name})

    if session.report_approved_by:
        rname = (reviewer_map or {}).get(session.report_approved_by) if reviewer_map is not None else None
        if rname is None:
            rname = db.query(User.full_name).filter(User.id == session.report_approved_by).scalar()
        if rname:
            out = out.model_copy(update={"report_approved_by_name": rname})

    if session.program:
        out = out.model_copy(update={
            "program_code": session.program.code,
            "program_name": session.program.name,
        })

    if session.sponsor:
        out = out.model_copy(update={"sponsor_name": session.sponsor.name})

    return out


def get_all_sessions(
    db: Session,
    county: str | None = None,
    skip: int = 0,
    limit: int = 50,
    created_by: str | None = None,
    q: str | None = None,
    approval_status: str | None = None,
    status: str | None = None,
    funding_source: str | None = None,
) -> tuple[list[SessionSummary], int]:
    query = _session_list_query(db)
    if county:
        query = query.filter(TrainingSession.county == county)
    if created_by:
        query = query.filter(TrainingSession.created_by == created_by)
    if approval_status:
        query = query.filter(TrainingSession.approval_status == approval_status)
    if status:
        query = query.filter(TrainingSession.status == status)
    if funding_source:
        query = query.filter(TrainingSession.funding_source.ilike(f"%{funding_source.strip()}%"))
    if q:
        like = f"%{q.strip()}%"
        query = query.filter(
            (TrainingSession.title.ilike(like))
            | (TrainingSession.facility.ilike(like))
            | (TrainingSession.venue.ilike(like))
            | (TrainingSession.funding_source.ilike(like))
            | (TrainingSession.county.ilike(like))
        )

    total = query.count()
    sessions = query.order_by(TrainingSession.created_at.desc()).offset(skip).limit(limit).all()

    reviewer_ids = {s.approved_by for s in sessions if s.approved_by} | \
                   {s.report_approved_by for s in sessions if s.report_approved_by}
    reviewer_map: dict[str, str] = {}
    if reviewer_ids:
        rows = db.query(User.id, User.full_name).filter(User.id.in_(reviewer_ids)).all()
        reviewer_map = {r.id: r.full_name for r in rows}

    return [to_session_summary(db, s, reviewer_map) for s in sessions], total


def get_session_or_404(db: Session, session_id: str) -> TrainingSession:
    s = _session_query(db).filter(TrainingSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    return s


def get_session_out_or_404(db: Session, session_id: str) -> SessionOut:
    return to_session_out(db, get_session_or_404(db, session_id))


def create_session(db: Session, data: SessionCreate, created_by: str) -> SessionOut:
    program_id = None
    if data.program_id:
        program = get_program_or_404(db, data.program_id)
        if not program.is_active:
            raise HTTPException(status_code=400, detail="Selected training program is not active.")
        program_id = program.id

    sponsor_id = (data.sponsor_id or "").strip() or None
    if sponsor_id:
        from app.services.catalog_service import get_sponsor_or_404
        get_sponsor_or_404(db, sponsor_id)

    s = TrainingSession(
        id=str(uuid.uuid4()),
        title=data.title,
        program_id=program_id,
        county=normalize_county(data.county),
        facility=data.facility,
        venue=(data.venue or "").strip() or None,
        funding_source=(data.funding_source or "").strip() or None,
        sponsor_id=sponsor_id,
        start_date=data.start_date,
        end_date=data.end_date,
        status=data.status,
        created_by=created_by,
    )
    db.add(s)
    db.flush()
    log_action(db, user_id=created_by, action="CREATE_SESSION",
               entity_type="session", entity_id=s.id, detail=s.title)
    db.commit()
    return get_session_out_or_404(db, s.id)


def update_session(
    db: Session, session: TrainingSession, data: SessionUpdate,
    user_id: str | None = None,
) -> SessionOut:
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
        if field == "program_id" and value is not None:
            program = get_program_or_404(db, value)
            if not program.is_active:
                raise HTTPException(status_code=400, detail="Selected training program is not active.")
            value = program.id
        if field in ("venue", "funding_source") and isinstance(value, str):
            value = value.strip() or None
        if field == "sponsor_id":
            value = (value or "").strip() or None
            if value:
                from app.services.catalog_service import get_sponsor_or_404
                get_sponsor_or_404(db, value)
        setattr(session, field, value)

    material_change = bool(updates.keys() & _APPROVAL_SENSITIVE_FIELDS)
    if material_change and session.approval_status == "APPROVED" and not session.certificates_issued:
        session.approval_status = "PENDING"
        session.approval_note = None

    log_action(db, user_id=user_id, action="UPDATE_SESSION",
               entity_type="session", entity_id=session.id,
               detail=", ".join(updates.keys()) if updates else None)
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def delete_session(
    db: Session, session: TrainingSession, user_id: str | None = None
) -> None:
    if session.certificates_issued:
        raise HTTPException(
            status_code=400,
            detail="Cannot delete a session after certificates have been issued.",
        )
    log_action(db, user_id=user_id, action="DELETE_SESSION",
               entity_type="session", entity_id=session.id, detail=session.title)
    db.delete(session)
    db.commit()


def complete_session(
    db: Session, session: TrainingSession, user_id: str | None = None
) -> SessionOut:
    """Mark training as completed (legacy Complete action) without requiring a report yet."""
    if session.approval_status != "APPROVED":
        raise HTTPException(status_code=400, detail="Session must be approved before it can be completed.")
    if session.certificates_issued:
        raise HTTPException(status_code=400, detail="Session already has certificates issued.")
    if session.status == "COMPLETED":
        raise HTTPException(status_code=400, detail="Session is already completed.")
    session.status = "COMPLETED"
    log_action(db, user_id=user_id, action="COMPLETE_SESSION",
               entity_type="session", entity_id=session.id)
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def approve_session(db: Session, session: TrainingSession, reviewed_by: str) -> SessionOut:
    if session.approval_status == "APPROVED":
        raise HTTPException(status_code=400, detail="Session is already approved.")
    session.approval_status = "APPROVED"
    session.approved_by     = reviewed_by
    session.approval_note   = None
    log_action(db, user_id=reviewed_by, action="APPROVE_SESSION",
               entity_type="session", entity_id=session.id)
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
    log_action(db, user_id=reviewed_by, action="REJECT_SESSION",
               entity_type="session", entity_id=session.id, detail=note)
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def submit_report(
    db: Session, session: TrainingSession, report: TrainingReportSchema,
    submitted_by: str | None = None,
) -> SessionOut:
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
    log_action(db, user_id=submitted_by, action="SUBMIT_REPORT",
               entity_type="session", entity_id=session.id)
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def approve_report(db: Session, session: TrainingSession, reviewed_by: str) -> SessionOut:
    if not session.report_submitted_at:
        raise HTTPException(status_code=400, detail="No report has been submitted for this session.")
    if session.report_approval_status == "APPROVED":
        raise HTTPException(status_code=400, detail="Report is already approved.")
    session.report_approval_status = "APPROVED"
    session.report_approval_note   = None
    session.report_approved_by     = reviewed_by
    log_action(db, user_id=reviewed_by, action="APPROVE_REPORT",
               entity_type="session", entity_id=session.id)
    db.commit()
    db.refresh(session)
    return to_session_out(db, session)


def reject_report(db: Session, session: TrainingSession, note: str, reviewed_by: str) -> SessionOut:
    if session.report_approval_status == "REJECTED":
        raise HTTPException(status_code=400, detail="Report is already rejected.")
    session.report_approval_status = "REJECTED"
    session.report_approval_note   = note
    session.report_approved_by     = reviewed_by
    log_action(db, user_id=reviewed_by, action="REJECT_REPORT",
               entity_type="session", entity_id=session.id, detail=note)
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
    name: str | None = None,
    cadre: str | None = None,
    facility: str | None = None,
    status: str = "PRESENT",
    staff_number: str | None = None,
    person_id: str | None = None,
    added_by: str | None = None,
) -> Participant:
    resolved_person_id = None
    if person_id:
        from app.services.person_service import get_person_or_404
        person = get_person_or_404(db, person_id)
        if not person.is_active:
            raise HTTPException(status_code=400, detail="Cannot add an inactive person.")
        if normalize_county(person.county) != normalize_county(session.county):
            raise HTTPException(
                status_code=400,
                detail="Person county must match the training session county.",
            )
        already = db.query(Participant).filter(
            Participant.session_id == session.id,
            Participant.person_id == person.id,
        ).first()
        if already:
            raise HTTPException(
                status_code=409,
                detail="This person is already enrolled in this session.",
            )
        resolved_person_id = person.id
        full_name = " ".join(
            p for p in [person.first_name, person.middle_name, person.last_name] if p
        )
        name = name or full_name
        cadre = cadre or person.qualification
        facility = facility or person.facility
        # Never copy national_id into staff_number — that breaks cert email lookup.

    if not name or not cadre or not facility:
        raise HTTPException(
            status_code=400,
            detail="name, cadre, and facility are required (or provide a valid person_id).",
        )

    p = Participant(
        id=str(uuid.uuid4()),
        session_id=session.id,
        person_id=resolved_person_id,
        name=name.strip(),
        cadre=cadre.strip(),
        facility=facility.strip(),
        status=status,
        staff_number=(staff_number or "").strip() or None,
    )
    db.add(p)
    db.flush()
    _sync_trainee_count(db, session)
    log_action(db, user_id=added_by, action="ADD_PARTICIPANT",
               entity_type="participant", entity_id=p.id,
               detail=f"{name} ({cadre}) — session {session.id}")
    db.commit()
    db.refresh(p)
    return p


def toggle_attendance(
    db: Session, session_id: str, participant_id: str,
    toggled_by: str | None = None,
) -> Participant:
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session_id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    p.status = "ABSENT" if p.status == "PRESENT" else "PRESENT"
    log_action(db, user_id=toggled_by, action="TOGGLE_ATTENDANCE",
               entity_type="participant", entity_id=participant_id,
               detail=f"→ {p.status}")
    db.commit()
    db.refresh(p)
    return p


def update_scores(
    db: Session,
    session_id: str,
    participant_id: str,
    pre: float | None,
    post: float | None,
    updated_by: str | None = None,
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
    log_action(db, user_id=updated_by, action="UPDATE_SCORES",
               entity_type="participant", entity_id=participant_id,
               detail=f"pre={pre} post={post}")
    db.commit()
    db.refresh(p)
    return p


def remove_participant(
    db: Session, session: TrainingSession, participant_id: str,
    removed_by: str | None = None,
) -> None:
    p = db.query(Participant).filter(
        Participant.id == participant_id,
        Participant.session_id == session.id
    ).first()
    if not p:
        raise HTTPException(status_code=404, detail="Participant not found.")
    log_action(db, user_id=removed_by, action="REMOVE_PARTICIPANT",
               entity_type="participant", entity_id=participant_id,
               detail=f"{p.name} — session {session.id}")
    db.delete(p)
    db.flush()
    _sync_trainee_count(db, session)
    db.commit()


# ── Trainers ───────────────────────────────────────────────────────────────────

def add_trainer(
    db: Session, session: TrainingSession, name: str, cadre: str, phone: str,
    added_by: str | None = None,
) -> SessionTrainer:
    t = SessionTrainer(
        id=str(uuid.uuid4()),
        session_id=session.id,
        name=name,
        cadre=cadre,
        phone=phone,
    )
    db.add(t)
    db.flush()
    log_action(db, user_id=added_by, action="ADD_TRAINER",
               entity_type="trainer", entity_id=t.id,
               detail=f"{name} ({cadre}) — session {session.id}")
    db.commit()
    db.refresh(t)
    return t


def remove_trainer(
    db: Session, session_id: str, trainer_id: str,
    removed_by: str | None = None,
) -> None:
    t = db.query(SessionTrainer).filter(
        SessionTrainer.id == trainer_id,
        SessionTrainer.session_id == session_id
    ).first()
    if not t:
        raise HTTPException(status_code=404, detail="Trainer not found.")
    log_action(db, user_id=removed_by, action="REMOVE_TRAINER",
               entity_type="trainer", entity_id=trainer_id,
               detail=f"{t.name} — session {session_id}")
    db.delete(t)
    db.commit()
