import csv
import io
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.session import TrainingSession
from app.models.participant import Participant
from app.services.legacy_certificate_service import PARTICIPANT_CSV_HEADERS
from app.services.session_service import _sync_trainee_count
from app.services.audit_service import log_action


def _parse_optional_float(value: str | None) -> float | None:
    if value is None or not str(value).strip():
        return None
    score = float(str(value).strip())
    if not (0 <= score <= 100):
        raise ValueError("Scores must be between 0 and 100")
    return score


def bulk_import_participants_csv(
    db: Session,
    session: TrainingSession,
    csv_text: str,
    *,
    added_by: str | None = None,
    max_rows: int = 500,
) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    headers = {h.strip().lower() for h in reader.fieldnames}
    required = {"name", "cadre", "facility"}
    missing = required - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    imported = 0
    errors: list[dict] = []
    rows = list(reader)
    if len(rows) > max_rows:
        raise HTTPException(status_code=400, detail=f"CSV exceeds maximum of {max_rows} rows per import.")

    for row_num, row in enumerate(rows, start=2):
        try:
            name = (row.get("name") or "").strip()
            cadre = (row.get("cadre") or "").strip()
            facility = (row.get("facility") or "").strip()
            if not name or not cadre or not facility:
                raise ValueError("name, cadre, and facility are required")

            status = (row.get("status") or "PRESENT").strip().upper()
            if status not in ("PRESENT", "ABSENT"):
                raise ValueError("status must be PRESENT or ABSENT")

            staff_number = (row.get("staff_number") or "").strip() or None
            pre_score = _parse_optional_float(row.get("pre_test_score"))
            post_score = _parse_optional_float(row.get("post_test_score"))

            p = Participant(
                id=str(uuid.uuid4()),
                session_id=session.id,
                name=name,
                cadre=cadre,
                facility=facility,
                status=status,
                staff_number=staff_number,
                pre_test_score=pre_score,
                post_test_score=post_score,
            )
            db.add(p)
            imported += 1
        except Exception as e:
            errors.append({"row": row_num, "message": str(e)})

    if imported:
        db.flush()
        _sync_trainee_count(db, session)
        log_action(
            db, user_id=added_by, action="BULK_IMPORT_PARTICIPANTS",
            entity_type="session", entity_id=session.id,
            detail=f"{imported} participant(s) imported via CSV",
        )
        db.commit()
    else:
        db.rollback()

    return {"imported": imported, "errors": errors}


def participant_csv_template() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(PARTICIPANT_CSV_HEADERS)
    writer.writerow(["Jane Wanjiku", "Nurse", "Kenyatta National Hospital", "MOH12345", "PRESENT", "70", "88"])
    writer.writerow(["John Kamau", "Clinical Officer", "Mbagathi Hospital", "", "PRESENT", "65", "82"])
    return buf.getvalue()
