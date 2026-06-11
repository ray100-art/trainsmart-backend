"""
TrainSMART — First-run seed script.
Creates the default System Administrator account.

Usage:
    1. Make sure your database is migrated first:
           alembic upgrade head
    2. Then run:
           python seed.py
"""
import sys
import os
import uuid

sys.path.insert(0, os.path.dirname(__file__))

from sqlalchemy.orm import Session
from app.database import engine
from app.models.user import User
from app.core.security import hash_password

# ── Admin credentials — change password after first login ─────────────────────
ADMIN_USERNAME = "admin"
ADMIN_EMAIL    = "admin@moh.go.ke"
ADMIN_PASSWORD = "Admin1234!"
ADMIN_FULLNAME = "System Administrator"
ADMIN_COUNTY   = "Nairobi"

with Session(engine) as db:
    existing = db.query(User).filter(User.username == ADMIN_USERNAME).first()
    if existing:
        print(f"✓ User '{ADMIN_USERNAME}' already exists — no action taken.")
    else:
        admin = User(
            id=str(uuid.uuid4()),
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            hashed_password=hash_password(ADMIN_PASSWORD),
            full_name=ADMIN_FULLNAME,
            role="ROLE_SYSTEM_ADMIN",
            county=ADMIN_COUNTY,
            is_active=True,
        )
        db.add(admin)
        db.commit()
        print("✓ Admin user created successfully!")
        print(f"  Username : {ADMIN_USERNAME}")
        print(f"  Password : {ADMIN_PASSWORD}")
        print(f"  Role     : ROLE_SYSTEM_ADMIN")
        print(f"\n⚠  Change this password immediately after first login.")
        print(f"   Log in at http://localhost:5173")