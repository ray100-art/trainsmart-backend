"""
Reset the admin password (local/ops use only).

Usage (Command Prompt or PowerShell):
    cd C:\\transmart-backend
    python scripts\\reset_admin_password.py YourNewPass1!

Password rules: 8+ chars, upper, lower, number, special character.
"""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal
from app.models.user import User
from app.core.security import hash_password
from app.services.auth_service import validate_password_strength


def main() -> None:
    if len(sys.argv) != 2:
        print("Usage: python scripts\\reset_admin_password.py YourNewPass1!")
        sys.exit(1)

    new_password = sys.argv[1]
    validate_password_strength(new_password)

    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == "admin").first()
        if not user:
            print("ERROR: user 'admin' was not found in the database.")
            sys.exit(1)

        user.hashed_password = hash_password(new_password)
        user.token_version = (user.token_version or 0) + 1
        user.setup_token = None
        user.setup_token_expires = None
        db.commit()
        print("OK: password updated for username 'admin'.")
        print("Log in, then change the password again from Profile.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
