"""
TrainSMART — First-run seed script.
Creates the default System Administrator account.

Usage:
    1. Make sure your database is migrated first:
           alembic upgrade head
    2. Then run:
           python seed.py

Credentials are written to a local file (never printed to stdout/logs).
Set ADMIN_CREDENTIALS_FILE to override the path (default: .admin_credentials).
"""
import sys
import os
import uuid
import secrets
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.database import engine
from app.models.user import User
from app.core.security import hash_password
from app.services.program_service import seed_default_programs

ADMIN_USERNAME = "admin"
ADMIN_EMAIL    = "admin@moh.go.ke"
ADMIN_FULLNAME = "System Administrator"
ADMIN_COUNTY   = "Nairobi"


def _credentials_path() -> Path:
    raw = os.environ.get("ADMIN_CREDENTIALS_FILE", ".admin_credentials")
    return Path(raw)


with Session(engine) as db:
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        print(f"User '{ADMIN_USERNAME}' already exists — no action taken.")
    else:
        admin_password = secrets.token_urlsafe(16)
        admin = User(
            id=str(uuid.uuid4()),
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(admin_password),
            full_name=ADMIN_FULLNAME,
            role="ROLE_SYSTEM_ADMIN",
            county=ADMIN_COUNTY,
            is_active=True,
            token_version=0,
        )
        db.add(admin)
        db.commit()

        cred_file = _credentials_path()
        cred_file.write_text(
            f"username={ADMIN_USERNAME}\npassword={admin_password}\nrole=ROLE_SYSTEM_ADMIN\n",
            encoding="utf-8",
        )
        try:
            os.chmod(cred_file, 0o600)
        except OSError:
            pass

        print("Admin user created successfully!")
        print(f"  Username : {ADMIN_USERNAME}")
        print(f"  Role     : ROLE_SYSTEM_ADMIN")
        print(f"  Credentials written to: {cred_file.resolve()}")
        print("  Open that file once, store the password securely, then delete the file.")
        print("  Password is NOT printed here (safe for deploy logs).")

    seeded = seed_default_programs(db)
    if seeded:
        print(f"\nSeeded {seeded} national training program(s) into the catalog.")
    else:
        print("\nTraining program catalog already populated.")
