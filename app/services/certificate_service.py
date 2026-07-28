import uuid
from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException, BackgroundTasks

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.models.user import User
from app.core.config import settings
from app.core.cache import verify_cache
from app.services.email_service import send_certificate_email
from app.services.session_service import to_session_out
from app.services.audit_service import log_action
from app.services.legacy_certificate_service import find_legacy_certificate, legacy_to_verify_dict
from app.schemas.session import SessionOut

_PIPELINE_OPTIONS = (
    selectinload(TrainingSession.program),
    selectinload(TrainingSession.sponsor),
)


def issue_certificates(
    db: Session,
    session_id: str,
    issued_by: str | None = None,
    background_tasks: BackgroundTasks | None = None,
) -> SessionOut:
    s = (
        db.query(TrainingSession)
        .options(
            selectinload(TrainingSession.participants).selectinload(Participant.person)
        )
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

    # Fix 5: guard against county names that produce an empty code
    county_code = ''.join(c for c in s.county if c.isalpha())[:3].upper() or "UNK"
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
        # Width grows past 999 so large sessions remain unique
        seq = f"{i:03d}" if i < 1000 else str(i)
        p.certificate_serial = f"MOH-TS-{county_code}-{year}-{session_short}-{seq}"

    s.certificates_issued = True
    log_action(db, user_id=issued_by, action="ISSUE_CERTIFICATES",
               entity_type="session", entity_id=session_id,
               detail=f"{len(eligible)} certificate(s) issued")
    db.commit()
    db.refresh(s)

    if settings.EMAIL_ENABLED:
        staff_numbers = {p.staff_number for p in eligible if p.staff_number and not (p.person and p.person.email)}
        users_by_staff: dict[str, User] = {}
        if staff_numbers:
            for u in db.query(User).filter(User.staff_number.in_(staff_numbers)).all():
                if u.staff_number:
                    users_by_staff[u.staff_number] = u

        for p in eligible:
            if not p.certificate_serial:
                continue

            # Prefer registry email, then staff_number → User, then unique name match.
            to_email = None
            if p.person_id and p.person and p.person.email:
                to_email = p.person.email
            elif p.staff_number and p.staff_number in users_by_staff:
                user = users_by_staff[p.staff_number]
                if user.email:
                    to_email = user.email
            elif not p.staff_number:
                matches = db.query(User).filter(User.full_name == p.name).all()
                if len(matches) == 1 and matches[0].email:
                    to_email = matches[0].email
                # len > 1 → ambiguous; skip rather than risk wrong recipient

            if to_email:
                def _send(email=to_email, name=p.name, serial=p.certificate_serial):
                    send_certificate_email(
                        to_email=email,
                        full_name=name,
                        course_title=s.title,
                        certificate_serial=serial,
                        county=s.county,
                        facility=p.facility,
                    )

                if background_tasks:
                    background_tasks.add_task(_send)
                else:
                    try:
                        _send()
                    except Exception as e:
                        import logging
                        logging.getLogger(__name__).warning(
                            "Certificate email failed for %s: %s", to_email, e
                        )

    return to_session_out(db, s)


def sign_certificates(
    db: Session,
    session_id: str,
    signed_by: str | None = None,
) -> SessionOut:
    """Mark issued certificates as signed (legacy Certificates → Signed)."""
    s = db.query(TrainingSession).filter(TrainingSession.id == session_id).first()
    if not s:
        raise HTTPException(status_code=404, detail="Session not found.")
    if not s.certificates_issued:
        raise HTTPException(status_code=400, detail="Issue certificates before signing them.")
    if s.certificates_signed:
        raise HTTPException(status_code=400, detail="Certificates are already signed.")
    s.certificates_signed = True
    log_action(db, user_id=signed_by, action="SIGN_CERTIFICATES",
               entity_type="session", entity_id=session_id)
    db.commit()
    db.refresh(s)
    return to_session_out(db, s)


def list_certificate_pipeline(
    db: Session,
    *,
    tab: str = "all",
    county: str | None = None,
    created_by: str | None = None,
    skip: int = 0,
    limit: int = 50,
) -> tuple[list[TrainingSession], int]:
    """Sessions in the certificate workflow: pending / certified / signed."""
    q = (
        db.query(TrainingSession)
        .options(*_PIPELINE_OPTIONS)
        .filter(TrainingSession.report_approval_status == "APPROVED")
    )
    if created_by:
        q = q.filter(TrainingSession.created_by == created_by)
    if county:
        q = q.filter(TrainingSession.county == county)
    if tab == "pending":
        q = q.filter(TrainingSession.certificates_issued.is_(False))
    elif tab == "certified":
        q = q.filter(
            TrainingSession.certificates_issued.is_(True),
            TrainingSession.certificates_signed.is_(False),
        )
    elif tab == "signed":
        q = q.filter(TrainingSession.certificates_signed.is_(True))
    total = q.count()
    items = q.order_by(TrainingSession.end_date.desc()).offset(skip).limit(limit).all()
    return items, total


def verify_certificate(db: Session, serial: str, era: str | None = None) -> dict:
    serial = serial.strip().upper()
    cache_key = f"{serial}|{era or '*'}"
    cached = verify_cache.get(cache_key)
    if cached is not None:
        return cached

    # Current system (TrainSMART v2+) — single query with session join
    p = (
        db.query(Participant)
        .options(joinedload(Participant.session))
        .filter(Participant.certificate_serial == serial)
        .first()
    )
    if p:
        s = p.session
        if not s:
            raise HTTPException(
                status_code=404,
                detail="Training session associated with this certificate no longer exists.",
            )
        result = {
            "valid": True,
            "source": "current",
            "era": "post_2018",
            "participant_name": p.name,
            "cadre": p.cadre,
            "facility": p.facility,
            "course": s.title,
            "county": s.county,
            "start_date": s.start_date.isoformat() if s.start_date else None,
            "end_date": s.end_date.isoformat() if s.end_date else None,
            "post_test_score": p.post_test_score,
            "issued_date": None,
            "serial": serial,
        }
        verify_cache.set(cache_key, result)
        return result

    # Legacy TrainSMART (migrated records)
    legacy = find_legacy_certificate(db, serial, era=era)
    if legacy:
        result = legacy_to_verify_dict(legacy)
        verify_cache.set(cache_key, result)
        return result

    if era == "pre_2018":
        detail = "Certificate not found in pre-2018 legacy records."
    elif era == "post_2018":
        detail = "Certificate not found in post-2018 records."
    else:
        detail = "Certificate not found. Check the serial number and certificate period."
    raise HTTPException(status_code=404, detail=detail)
