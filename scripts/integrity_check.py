"""Read-only (default) integrity checks for TrainSMART.

Usage:
  python scripts/integrity_check.py
  python scripts/integrity_check.py --fix   # safe cleanups only

Never prints DATABASE_URL or secrets. Exit code 1 if any report-only check finds rows.
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import text

from app.database import SessionLocal


# (name, sql, severity) — severity: "error" fails exit; "warn" prints only
CHECKS: list[tuple[str, str, str]] = [
    (
        "dangling_person_fk",
        """
        SELECT p.id FROM participants p
        LEFT JOIN people pe ON pe.id = p.person_id
        WHERE p.person_id IS NOT NULL AND pe.id IS NULL
        """,
        "error",
    ),
    (
        "cert_flags_inconsistent",
        """
        SELECT s.id FROM training_sessions s
        LEFT JOIN participants p ON p.session_id = s.id
        GROUP BY s.id, s.certificates_issued, s.certificates_signed
        HAVING (s.certificates_issued = true AND COUNT(p.certificate_serial) = 0)
            OR (s.certificates_signed = true AND s.certificates_issued = false)
            OR (s.certificates_issued = false AND COUNT(p.certificate_serial) > 0)
        """,
        "error",
    ),
    (
        "certs_issued_but_report_not_approved",
        """
        SELECT id FROM training_sessions
        WHERE certificates_issued = true
          AND report_approval_status IS DISTINCT FROM 'APPROVED'
        """,
        "error",
    ),
    (
        "trainee_count_drift",
        """
        SELECT s.id FROM training_sessions s
        LEFT JOIN participants p ON p.session_id = s.id
        GROUP BY s.id, s.trainee_count
        HAVING s.trainee_count IS DISTINCT FROM COUNT(p.id)
        """,
        "warn",
    ),
    (
        "live_legacy_serial_collision",
        """
        SELECT p.certificate_serial FROM participants p
        JOIN legacy_certificates l ON UPPER(l.serial) = UPPER(p.certificate_serial)
        WHERE p.certificate_serial IS NOT NULL
        """,
        "error",
    ),
    (
        "duplicate_person_enrollment",
        """
        SELECT session_id || ':' || person_id FROM participants
        WHERE person_id IS NOT NULL
        GROUP BY session_id, person_id
        HAVING COUNT(*) > 1
        """,
        "error",
    ),
    (
        "expired_setup_tokens",
        """
        SELECT id FROM users
        WHERE setup_token IS NOT NULL
          AND setup_token_expires < NOW()
        """,
        "warn",
    ),
    (
        "deactivated_with_mfa_secret",
        """
        SELECT id FROM users
        WHERE is_active = false AND mfa_secret IS NOT NULL
        """,
        "warn",
    ),
    (
        "stale_pending_session_approval",
        """
        SELECT id FROM training_sessions
        WHERE approval_status = 'PENDING'
          AND end_date < CURRENT_DATE - INTERVAL '90 days'
        """,
        "warn",
    ),
    (
        "upcoming_past_end_date",
        """
        SELECT id FROM training_sessions
        WHERE status = 'UPCOMING' AND end_date < CURRENT_DATE
        """,
        "warn",
    ),
    (
        "old_rate_limit_events",
        """
        SELECT id::text FROM rate_limit_events
        WHERE created_at < NOW() - INTERVAL '7 days'
        LIMIT 5000
        """,
        "warn",
    ),
]


def _sample_ids(rows: list, limit: int = 5) -> str:
    ids = [str(r[0]) for r in rows[:limit]]
    return ", ".join(ids) if ids else ""


def run_checks(*, fix: bool) -> int:
    db = SessionLocal()
    failed = 0
    try:
        print(f"TrainSMART integrity check · {datetime.now(timezone.utc).isoformat()}")
        print(f"Mode: {'FIX' if fix else 'REPORT-ONLY'}")
        print("-" * 60)

        for name, sql, severity in CHECKS:
            rows = db.execute(text(sql)).fetchall()
            n = len(rows)
            mark = "OK" if n == 0 else severity.upper()
            sample = _sample_ids(rows)
            suffix = f"  sample=[{sample}]" if sample else ""
            print(f"[{mark}] {name}: {n}{suffix}")
            if n and severity == "error":
                failed += 1

        if fix:
            print("-" * 60)
            print("Applying safe cleanups…")

            r1 = db.execute(text("""
                UPDATE users
                SET setup_token = NULL, setup_token_expires = NULL
                WHERE setup_token IS NOT NULL
                  AND setup_token_expires < NOW()
            """))
            print(f"  cleared expired setup tokens: {r1.rowcount}")

            r2 = db.execute(text("""
                UPDATE users
                SET mfa_enabled = false, mfa_secret = NULL
                WHERE is_active = false AND mfa_secret IS NOT NULL
            """))
            print(f"  cleared MFA on deactivated users: {r2.rowcount}")

            r3 = db.execute(text("""
                UPDATE training_sessions s
                SET trainee_count = sub.actual
                FROM (
                    SELECT s2.id, COUNT(p.id) AS actual
                    FROM training_sessions s2
                    LEFT JOIN participants p ON p.session_id = s2.id
                    GROUP BY s2.id
                ) sub
                WHERE s.id = sub.id
                  AND s.trainee_count IS DISTINCT FROM sub.actual
            """))
            print(f"  reconciled trainee_count: {r3.rowcount}")

            r4 = db.execute(text("""
                DELETE FROM rate_limit_events
                WHERE created_at < NOW() - INTERVAL '7 days'
            """))
            print(f"  purged old rate_limit_events: {r4.rowcount}")

            # Clear stale approved_by when approval was reset to PENDING
            r5 = db.execute(text("""
                UPDATE training_sessions
                SET approved_by = NULL
                WHERE approval_status = 'PENDING' AND approved_by IS NOT NULL
            """))
            print(f"  cleared stale approved_by on PENDING sessions: {r5.rowcount}")

            db.commit()
            print("Fixes committed.")

        print("-" * 60)
        if failed:
            print(f"RESULT: {failed} error-level issue(s) found.")
            return 1
        print("RESULT: no error-level integrity issues.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="TrainSMART data integrity checks")
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Apply safe cleanups (expired tokens, deactivated MFA, trainee_count, old rate limits)",
    )
    args = parser.parse_args()
    raise SystemExit(run_checks(fix=args.fix))
