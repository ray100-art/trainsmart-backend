import csv
import io
from datetime import date

from sqlalchemy import func, case, and_
from sqlalchemy.orm import Session

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.models.training_program import TrainingProgram


def _session_filters(county: str | None = None, created_by: str | None = None) -> list:
    filters = []
    if county:
        filters.append(TrainingSession.county == county)
    if created_by:
        filters.append(TrainingSession.created_by == created_by)
    return filters


def get_overview_stats(
    db: Session,
    county: str | None = None,
    created_by: str | None = None,
) -> dict:
    filters = _session_filters(county, created_by)

    row = db.query(
        func.count(TrainingSession.id).label("total"),
        func.count(case((TrainingSession.approval_status == "APPROVED", 1))).label("approved"),
        func.count(case((TrainingSession.status == "COMPLETED", 1))).label("completed"),
        func.count(case((TrainingSession.certificates_issued.is_(True), 1))).label("certs_issued"),
        func.count(case((TrainingSession.approval_status == "PENDING", 1))).label("pending_session"),
        func.count(case((TrainingSession.approval_status == "REJECTED", 1))).label("rejected_session"),
        func.count(case((TrainingSession.status == "IN_PROGRESS", 1))).label("in_progress"),
        func.count(case((and_(
            TrainingSession.report_submitted_at.isnot(None),
            TrainingSession.report_approval_status == "PENDING",
        ), 1))).label("pending_report"),
        func.count(case((TrainingSession.report_approval_status == "REJECTED", 1))).label("rejected_report"),
        func.count(case((and_(
            TrainingSession.report_approval_status == "APPROVED",
            TrainingSession.certificates_issued.is_(False),
        ), 1))).label("ready_certs"),
        func.count(case((and_(
            TrainingSession.approval_status == "APPROVED",
            TrainingSession.status == "COMPLETED",
            TrainingSession.report_submitted_at.is_(None),
        ), 1))).label("report_due"),
    ).filter(*filters).one()

    participant_q = db.query(
        func.count(Participant.id).label("total"),
        func.count(case((Participant.certificate_serial.isnot(None), 1))).label("certified"),
        func.count(case((Participant.status == "PRESENT", 1))).label("present"),
    )
    if county or created_by:
        participant_q = participant_q.join(
            TrainingSession, Participant.session_id == TrainingSession.id
        )
        if county:
            participant_q = participant_q.filter(TrainingSession.county == county)
        if created_by:
            participant_q = participant_q.filter(TrainingSession.created_by == created_by)
    prow = participant_q.one()

    county_rows = (
        db.query(TrainingSession.county, func.count(TrainingSession.id).label("cnt"))
        .filter(*filters)
        .group_by(TrainingSession.county)
        .order_by(func.count(TrainingSession.id).desc())
        .all()
    )

    return {
        "total_sessions":               row.total,
        "approved_sessions":            row.approved,
        "completed_sessions":           row.completed,
        "in_progress_sessions":         row.in_progress,
        "certificates_issued_sessions": row.certs_issued,
        "pending_session_approvals":    row.pending_session,
        "rejected_sessions":            row.rejected_session,
        "pending_report_approvals":     row.pending_report,
        "rejected_reports":             row.rejected_report,
        "ready_for_certificates":       row.ready_certs,
        "reports_due":                  row.report_due,
        "total_participants":           prow.total,
        "certified_participants":       prow.certified,
        "present_participants":         prow.present,
        "sessions_by_county":           {r.county: r.cnt for r in county_rows},
    }


def get_analytics(db: Session, county: str | None = None) -> dict:
    """National / M&E analytics: cadre breakdown and session status distribution."""
    filters = _session_filters(county)

    cadre_rows = (
        db.query(Participant.cadre, func.count(Participant.id).label("cnt"))
        .join(TrainingSession, Participant.session_id == TrainingSession.id)
        .filter(*filters)
        .group_by(Participant.cadre)
        .order_by(func.count(Participant.id).desc())
        .all()
    )

    status_rows = (
        db.query(TrainingSession.status, func.count(TrainingSession.id).label("cnt"))
        .filter(*filters)
        .group_by(TrainingSession.status)
        .all()
    )

    approval_rows = (
        db.query(TrainingSession.approval_status, func.count(TrainingSession.id).label("cnt"))
        .filter(*filters)
        .group_by(TrainingSession.approval_status)
        .all()
    )

    return {
        "participants_by_cadre": {r.cadre: r.cnt for r in cadre_rows},
        "sessions_by_status":    {r.status: r.cnt for r in status_rows},
        "sessions_by_approval":  {r.approval_status: r.cnt for r in approval_rows},
    }


def export_sessions_csv(db: Session, county: str | None = None) -> str:
    """Export session summary as CSV for M&E reporting (capped to EXPORT_MAX_ROWS)."""
    from app.core.config import settings

    filters = _session_filters(county)
    sessions = (
        db.query(TrainingSession)
        .filter(*filters)
        .order_by(TrainingSession.start_date.desc())
        .limit(settings.EXPORT_MAX_ROWS)
        .all()
    )

    program_ids = {s.program_id for s in sessions if s.program_id}
    program_map: dict[str, str] = {}
    if program_ids:
        for pid, code in db.query(TrainingProgram.id, TrainingProgram.code).filter(
            TrainingProgram.id.in_(program_ids)
        ).all():
            program_map[pid] = code

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Session ID", "Program Code", "Title", "County", "Facility", "Start Date", "End Date",
        "Status", "Approval", "Participants", "Report Status", "Certificates Issued",
    ])
    for s in sessions:
        writer.writerow([
            s.id,
            program_map.get(s.program_id, "") if s.program_id else "",
            s.title,
            s.county,
            s.facility,
            s.start_date.isoformat() if s.start_date else "",
            s.end_date.isoformat() if s.end_date else "",
            s.status,
            s.approval_status,
            s.trainee_count,
            s.report_approval_status,
            "Yes" if s.certificates_issued else "No",
        ])
    return buf.getvalue()


def export_participants_csv(db: Session, county: str | None = None) -> str:
    """Export participant-level data for national M&E reporting (capped to EXPORT_MAX_ROWS)."""
    from app.core.config import settings

    filters = _session_filters(county)
    rows = (
        db.query(Participant, TrainingSession)
        .join(TrainingSession, Participant.session_id == TrainingSession.id)
        .filter(*filters)
        .order_by(TrainingSession.start_date.desc(), Participant.name)
        .limit(settings.EXPORT_MAX_ROWS)
        .all()
    )

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "Participant Name", "Cadre", "Facility", "Staff Number", "Attendance",
        "Pre-test", "Post-test", "Certificate Serial", "Session Title", "County",
        "Session Start", "Session End", "Session Status",
    ])
    for p, s in rows:
        writer.writerow([
            p.name, p.cadre, p.facility, p.staff_number or "",
            p.status, p.pre_test_score or "", p.post_test_score or "",
            p.certificate_serial or "", s.title, s.county,
            s.start_date.isoformat() if s.start_date else "",
            s.end_date.isoformat() if s.end_date else "",
            s.status,
        ])
    return buf.getvalue()
