#!/usr/bin/env python3
"""
Import legacy TrainSMART certificates from CSV into PostgreSQL.

Usage:
    python scripts/import_legacy_certificates.py path/to/legacy_certs.csv

CSV columns (header required):
    serial, participant_name, cadre, facility, course, county,
    start_date, end_date, post_test_score, issued_date, era

era: pre_2018 | post_2018
"""
import sys
from pathlib import Path

# Allow running from repo root
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.database import SessionLocal
from app.services.legacy_certificate_service import import_legacy_csv


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"File not found: {path}")
        return 1

    text = path.read_text(encoding="utf-8-sig")
    db = SessionLocal()
    try:
        result = import_legacy_csv(db, text, skip_duplicates=True)
        print(f"Imported: {result['imported']}")
        print(f"Skipped (duplicates): {result['skipped']}")
        if result["errors"]:
            print(f"Errors: {len(result['errors'])}")
            for err in result["errors"][:20]:
                print(f"  Row {err['row']}: {err['message']}")
        return 0 if not result["errors"] or result["imported"] else 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
