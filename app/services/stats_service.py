from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.session import TrainingSession
from app.models.participant import Participant


def get_overview_stats(db: Session, county: str | None = None) -> dict:
    q = db.query(TrainingSession)
    if county:
        q = q.filter(TrainingSession.county == county)
    sessions = q.all()

    total_sessions = len(sessions)
    approved_sessions = sum(1 for s in sessions if s.approval_status == "APPROVED")
    completed_sessions = sum(1 for s in sessions if s.status == "COMPLETED")
    certs_issued = sum(1 for s in sessions if s.certificates_issued)
    pending_session_approval = sum(1 for s in sessions if s.approval_status == "PENDING")
    pending_report_approval = sum(
        1 for s in sessions
        if s.report_submitted_at and s.report_approval_status == "PENDING"
    )
    ready_for_certs = sum(
        1 for s in sessions
        if s.report_approval_status == "APPROVED" and not s.certificates_issued
    )

    session_ids = [s.id for s in sessions]
    total_participants = 0
    certified_participants = 0
    if session_ids:
        total_participants = db.query(func.count(Participant.id)).filter(
            Participant.session_id.in_(session_ids)
        ).scalar() or 0
        certified_participants = db.query(func.count(Participant.id)).filter(
            Participant.session_id.in_(session_ids),
            Participant.certificate_serial.isnot(None),
        ).scalar() or 0

    by_county: dict[str, int] = {}
    for s in sessions:
        by_county[s.county] = by_county.get(s.county, 0) + 1

    return {
        "total_sessions": total_sessions,
        "approved_sessions": approved_sessions,
        "completed_sessions": completed_sessions,
        "certificates_issued_sessions": certs_issued,
        "pending_session_approvals": pending_session_approval,
        "pending_report_approvals": pending_report_approval,
        "ready_for_certificates": ready_for_certs,
        "total_participants": total_participants,
        "certified_participants": certified_participants,
        "sessions_by_county": by_county,
    }
