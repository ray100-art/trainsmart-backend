# TranSMART — Bug Fix Files

Replace each file at the path shown. No other files need to change.

---

## .env
**Path:** `transmart-backend/.env`
**Fix:** SECRET_KEY was the placeholder string — the config validator rejects it and
the server won't start. Replaced with a real 64-char hex key.

> If deploying to production, generate your own:
>   python -c "import secrets; print(secrets.token_hex(32))"

---

## certificate_service.py
**Path:** `transmart-backend/app/services/certificate_service.py`
**Fix:** Serial numbers collided across sessions. Two sessions in the same county
both generated `MOH-TS-NAI-2026-001`, hitting the UNIQUE constraint on the second
commit. Now includes the first 6 chars of the session UUID in the serial:
  MOH-TS-{COUNTY}-{YEAR}-{SESSION_SHORT}-{NNN}
Also added a guard that raises 400 if there are no eligible participants, and
uses the actual session year instead of the hardcoded "2026".

---

## session_service.py
**Path:** `transmart-backend/app/services/session_service.py`
**Fixes:**
1. trainee_count was never updated — always stayed at 0. add_participant now
   increments it and remove_participant decrements it (clamped to 0).
2. add_participant now accepts and uses the `status` parameter instead of
   ignoring it and hardcoding "PRESENT".

---

## participants.py
**Path:** `transmart-backend/app/routers/participants.py`
**Fix:** The add_participant route was not passing data.status to the service.
Now passes it through so the caller's value is respected.

---

## auth.py
**Path:** `transmart-backend/app/routers/auth.py`
**Fix:** POST /auth/register was completely open — any unauthenticated user could
self-register with any role including ROLE_NATIONAL_ADMIN. Now requires
ROLE_SYSTEM_ADMIN to create accounts.