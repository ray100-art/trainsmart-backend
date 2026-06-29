import csv
import io
import uuid
from datetime import date, datetime

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.legacy_certificate import LegacyCertificate

VALID_ERAS = frozenset({"pre_2018", "post_2018"})

LEGACY_CSV_HEADERS = [
    "serial", "participant_name", "cadre", "facility", "course", "county",
    "start_date", "end_date", "post_test_score", "issued_date", "era",
]

PARTICIPANT_CSV_HEADERS = [
    "name", "cadre", "facility", "staff_number", "status", "pre_test_score", "post_test_score",
]


def _parse_date(value: str | None) -> date | None:
    if not value or not str(value).strip():
        return None
    raw = str(value).strip()[:10]
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y"):
        try:
            return datetime.strptime(raw, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {value}")


def _normalize_era(value: str) -> str:
    v = value.strip().lower().replace("-", "_").replace(" ", "_")
    if v in ("pre_2018", "pre2018", "before_2018", "before"):
        return "pre_2018"
    if v in ("post_2018", "post2018", "after_2018", "after"):
        return "post_2018"
    raise ValueError(f"era must be pre_2018 or post_2018, got '{value}'")


def legacy_to_verify_dict(cert: LegacyCertificate) -> dict:
    return {
        "valid": True,
        "source": "legacy",
        "era": cert.era,
        "participant_name": cert.participant_name,
        "cadre": cert.cadre,
        "facility": cert.facility,
        "course": cert.course,
        "county": cert.county,
        "start_date": cert.start_date.isoformat() if cert.start_date else None,
        "end_date": cert.end_date.isoformat() if cert.end_date else None,
        "post_test_score": cert.post_test_score,
        "issued_date": cert.issued_date.isoformat() if cert.issued_date else None,
        "serial": cert.serial,
    }


def find_legacy_certificate(
    db: Session, serial: str, era: str | None = None,
) -> LegacyCertificate | None:
    q = db.query(LegacyCertificate).filter(LegacyCertificate.serial == serial)
    if era:
        q = q.filter(LegacyCertificate.era == era)
    return q.first()


def import_legacy_csv(db: Session, csv_text: str, *, skip_duplicates: bool = True) -> dict:
    reader = csv.DictReader(io.StringIO(csv_text))
    if not reader.fieldnames:
        raise HTTPException(status_code=400, detail="CSV file is empty or has no header row.")

    headers = {h.strip().lower() for h in reader.fieldnames}
    required = {"serial", "participant_name", "cadre", "facility", "course", "county", "era"}
    missing = required - headers
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"CSV missing required columns: {', '.join(sorted(missing))}",
        )

    imported = 0
    skipped = 0
    errors: list[dict] = []

    for row_num, row in enumerate(reader, start=2):
        try:
            serial = (row.get("serial") or "").strip().upper()
            if not serial:
                raise ValueError("serial is required")

            existing = db.query(LegacyCertificate).filter(LegacyCertificate.serial == serial).first()
            if existing:
                if skip_duplicates:
                    skipped += 1
                    continue
                raise ValueError(f"serial already exists: {serial}")

            era = _normalize_era(row.get("era") or "post_2018")
            score_raw = (row.get("post_test_score") or "").strip()
            post_score = float(score_raw) if score_raw else None
            if post_score is not None and not (0 <= post_score <= 100):
                raise ValueError("post_test_score must be 0–100")

            cert = LegacyCertificate(
                id=str(uuid.uuid4()),
                serial=serial,
                participant_name=(row.get("participant_name") or "").strip(),
                cadre=(row.get("cadre") or "").strip(),
                facility=(row.get("facility") or "").strip(),
                course=(row.get("course") or "").strip(),
                county=(row.get("county") or "").strip(),
                start_date=_parse_date(row.get("start_date")),
                end_date=_parse_date(row.get("end_date")),
                post_test_score=post_score,
                issued_date=_parse_date(row.get("issued_date")),
                era=era,
            )
            if not cert.participant_name or not cert.cadre or not cert.facility or not cert.course or not cert.county:
                raise ValueError("participant_name, cadre, facility, course, and county are required")

            db.add(cert)
            imported += 1
        except Exception as e:
            errors.append({"row": row_num, "message": str(e)})

    if imported:
        db.commit()
    else:
        db.rollback()

    return {"imported": imported, "skipped": skipped, "errors": errors}


def legacy_csv_template() -> str:
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(LEGACY_CSV_HEADERS)
    writer.writerow([
        "MOH-LEG-NAI-2017-00001", "Jane Wanjiku", "Nurse", "Kenyatta National Hospital",
        "HIV Integrated Training", "Nairobi", "2017-06-01", "2017-06-05", "85", "2017-06-10", "pre_2018",
    ])
    return buf.getvalue()
