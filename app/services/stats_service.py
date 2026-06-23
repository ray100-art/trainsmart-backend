from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.models.session import TrainingSession
from app.models.participant import Participant


def get_overview_stats(db: Session, county: str | None = None) -> dict:
    county_filter = [TrainingSession.county == county] if county else []

    # All session-level counts in a single SQL pass
    row = db.query(
        func.count(TrainingSession.id).label("total"),
        func.count(case((TrainingSession.approval_status == "APPROVED", 1))).label("approved"),
        func.count(case((TrainingSession.status == "COMPLETED", 1))).label("completed"),
        func.count(case((TrainingSession.certificates_issued.is_(True), 1))).label("certs_issued"),
        func.count(case((TrainingSession.approval_status == "PENDING", 1))).label("pending_session"),
        func.count(case((and_(
            TrainingSession.report_submitted_at.isnot(None),
            TrainingSession.report_approval_status == "PENDING",
        ), 1))).label("pending_report"),
        func.count(case((and_(
            TrainingSession.report_approval_status == "APPROVED",
            TrainingSession.certificates_issued.is_(False),
        ), 1))).label("ready_certs"),
    ).filter(*county_filter).one()

    # Participant counts — join only when filtering by county
    participant_q = db.query(
        func.count(Participant.id).label("total"),
        func.count(case((Participant.certificate_serial.isnot(None), 1))).label("certified"),
    )
    if county:
        participant_q = participant_q.join(
            TrainingSession, Participant.session_id == TrainingSession.id
        ).filter(TrainingSession.county == county)
    prow = participant_q.one()

    # Per-county session breakdown
    county_rows = (
        db.query(TrainingSession.county, func.count(TrainingSession.id).label("cnt"))
        .filter(*county_filter)
        .group_by(TrainingSession.county)
        .all()
    )

    return {
        "total_sessions":              row.total,
        "approved_sessions":           row.approved,
        "completed_sessions":          row.completed,
        "certificates_issued_sessions": row.certs_issued,
        "pending_session_approvals":   row.pending_session,
        "pending_report_approvals":    row.pending_report,
        "ready_for_certificates":      row.ready_certs,
        "total_participants":          prow.total,
        "certified_participants":      prow.certified,
        "sessions_by_county":          {r.county: r.cnt for r in county_rows},
    }
