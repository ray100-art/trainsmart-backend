import uuid
from sqlalchemy.orm import Session, selectinload
from fastapi import HTTPException, BackgroundTasks

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.models.user import User
from app.core.config import settings
from app.services.email_service import send_certificate_email
from app.services.session_service import to_session_out
from app.schemas.session import SessionOut


def issue_certificates(db: Session, session_id: str, background_tasks: BackgroundTasks | None = None) -> SessionOut:
    s = (
        db.query(TrainingSession)
        .options(selectinload(TrainingSession.participants))
        .filter(TrainingSession.id == session_id)
        .with_for_update()
        .first()
    )
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    if s.report_approval_status != "APPROVED":
        raise HTTPException(status_code=400, detail="Report must be approved before issuing certificates.")
    if s.certificates_issued:
        raise HTTPException(status_code=400, detail="Certificates already issued for this session.")

    county_code = ''.join(c for c in s.county if c.isalpha())[:3].upper()
    session_short = s.id.replace('-', '')[:6].upper()

    eligible = [
        p for p in s.participants
        if p.status == "PRESENT" and (p.post_test_score or 0) >= 80 and not p.certificate_serial
    ]

    if not eligible:
        raise HTTPException(
            status_code=400,
            detail="No eligible participants (must be PRESENT with post-test score >= 80).",
        )

    year = str(s.start_date.year) if s.start_date else "2026"
    existing_serials = sum(1 for p in s.participants if p.certificate_serial)

    for i, p in enumerate(eligible, start=existing_serials + 1):
        p.certificate_serial = f"MOH-TS-{county_code}-{year}-{session_short}-{str(i).zfill(3)}"

    s.certificates_issued = True
    db.commit()
    db.refresh(s)

    if settings.EMAIL_ENABLED:
        for p in eligible:
            if p.certificate_serial:
                user = None
                if p.staff_number:
                    user = db.query(User).filter(User.staff_number == p.staff_number).first()
                if not user:
                    user = db.query(User).filter(User.full_name == p.name).first()
                if user and user.email:
                    if background_tasks:
                        background_tasks.add_task(
                            send_certificate_email,
                            to_email=user.email,
                            full_name=p.name,
                            course_title=s.title,
                            certificate_serial=p.certificate_serial,
                            county=s.county,
                            facility=p.facility,
                        )
                    else:
                        try:
                            send_certificate_email(
                                to_email=user.email,
                                full_name=p.name,
                                course_title=s.title,
                                certificate_serial=p.certificate_serial,
                                county=s.county,
                                facility=p.facility,
                            )
                        except Exception as e:
                            print(f"[EMAIL WARNING] Certificate email failed for {user.email}: {e}")

    return to_session_out(db, s)


def verify_certificate(db: Session, serial: str) -> dict:
    serial = serial.strip().upper()
    p = db.query(Participant).filter(Participant.certificate_serial == serial).first()
    if not p:
        raise HTTPException(status_code=404, detail="Certificate not found.")

    s = db.query(TrainingSession).filter(TrainingSession.id == p.session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Training session associated with this certificate no longer exists.")

    return {
        "valid":            True,
        "participant_name": p.name,
        "cadre":            p.cadre,
        "facility":         p.facility,
        "course":           s.title,
        "county":           s.county,
        "start_date":       s.start_date.isoformat() if s.start_date else None,
        "end_date":         s.end_date.isoformat() if s.end_date else None,
        "post_test_score":  p.post_test_score,
        "serial":           serial,
    }
