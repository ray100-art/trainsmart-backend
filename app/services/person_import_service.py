import csv
import io
import uuid

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.person import Person
from app.lib.county import normalize_county
from app.services.audit_service import log_action

PEOPLE_CSV_HEADERS = [
    "national_id", "first_name", "middle_name", "last_name", "gender",
    "qualification", "facility", "county", "phone", "email",
]


def people_csv_template() -> str:
    return ",".join(PEOPLE_CSV_HEADERS) + "\n"


def bulk_import_people_csv(
    db: Session,
    csv_text: str,
    *,
    created_by: str | None = None,
    force_county: str | None = None,
    max_rows: int = 2000,
) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    headers = {h.strip().lower() for h in reader.fieldnames}
    required = {"national_id", "first_name", "last_name", "gender", "qualification", "facility", "county"}
    missing = required - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    imported = 0
    skipped = 0
    errors: list[dict] = []
    rows = list(reader)
    if len(rows) > max_rows:
        raise HTTPException(status_code=400, detail=f"CSV exceeds maximum of {max_rows} rows per import.")

    for row_num, row in enumerate(rows, start=2):
        try:
            national_id = (row.get("national_id") or "").strip()
            first_name = (row.get("first_name") or "").strip()
            last_name = (row.get("last_name") or "").strip()
            gender = (row.get("gender") or "").strip()
            qualification = (row.get("qualification") or "").strip()
            facility = (row.get("facility") or "").strip()
            county = force_county or (row.get("county") or "").strip()
            if not all([national_id, first_name, last_name, gender, qualification, facility, county]):
                raise ValueError("required fields missing")
            if gender not in ("Male", "Female", "Other"):
                raise ValueError("gender must be Male, Female, or Other")

            existing = db.query(Person).filter(Person.national_id == national_id).first()
            if existing:
                skipped += 1
                continue

            person = Person(
                id=str(uuid.uuid4()),
                national_id=national_id,
                first_name=first_name,
                middle_name=(row.get("middle_name") or "").strip() or None,
                last_name=last_name,
                gender=gender,
                qualification=qualification,
                facility=facility,
                county=normalize_county(county),
                phone=(row.get("phone") or "").strip() or None,
                email=(row.get("email") or "").strip() or None,
                created_by=created_by,
            )
            db.add(person)
            imported += 1
        except Exception as e:
            errors.append({"row": row_num, "error": str(e)})

    if imported:
        log_action(
            db, user_id=created_by, action="IMPORT_PEOPLE",
            entity_type="person", entity_id="bulk",
            detail=f"imported={imported} skipped={skipped} errors={len(errors)}",
        )
        db.commit()
    else:
        db.rollback()

    return {
        "imported": imported,
        "skipped": skipped,
        "errors": errors[:50],
        "error_count": len(errors),
    }
