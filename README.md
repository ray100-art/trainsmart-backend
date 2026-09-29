# TrainSMART Backend

FastAPI + PostgreSQL API for **TrainSMART**, a national registry for healthcare-worker training in
Kenya: training sessions, participants, attendance and scores, a certificate approval pipeline,
and public certificate verification.

> **Status:** independently designed and built by [Brian Ndung'u](https://github.com/ray100-art) as a
> proposed replacement for NASCOP's legacy TrainSMART registry. It is **not** an official Ministry of
> Health deployment. The live instance is a demo.

**Live demo:** [trainsmart-fronted.vercel.app](https://trainsmart-fronted.vercel.app) ·
**Frontend:** [ray100-art/trainsmart-fronted](https://github.com/ray100-art/trainsmart-fronted)

`Python 3.12` `FastAPI` `SQLAlchemy 2` `PostgreSQL` `Alembic` `Pydantic v2` `pytest` `GitHub Actions` `Docker` `Nginx`

---

## What it does

| Area | Capabilities |
|------|--------------|
| **Training sessions** | Create, edit, complete; national approve / reject; post-training report submission and approval |
| **Participants** | Register attendees per session, record attendance and pre/post-test scores, bulk CSV import |
| **People registry** | Deduplicated person records across sessions, facility and sponsor catalogues, CSV import |
| **Certificates** | Issue → sign pipeline; public verification by serial number, covering current and pre-2018 legacy certificates |
| **Legacy migration** | CSV import of historical certificates so old serials still verify |
| **Reporting** | Overview and analytics endpoints, CSV exports of sessions and participants |
| **Administration** | User accounts via invitation and password setup, activation and deactivation, full audit log |

## Security and data integrity

- **Role-based access control** with six roles (trainer, site coordinator, county officer, national admin,
  M&E manager, system admin). County and site roles are scoped to their own data.
- **Cookie-based JWT auth with CSRF protection** (double-submit token). Logout revokes sessions through a
  `token_version` bump.
- **TOTP multi-factor authentication** for privileged roles, switched by configuration (`MFA_ENABLED`, `MFA_ENFORCE_PRIVILEGED`).
- **Rate limiting** on login, forgot-password and public certificate verification, using the real client IP behind a proxy.
- **Audit log** of authentication and data-changing events, including the client IP.
- **No default credentials:** `seed.py` generates a random admin password and writes it to a one-time file.
- **Integrity tooling:** `scripts/integrity_check.py` reports orphaned or inconsistent rows and can apply safe cleanups.
- Swagger/ReDoc docs are disabled when `ENVIRONMENT=production`.

## Architecture

```
app/
  routers/    HTTP layer: auth, sessions, participants, people, certificates, stats, audit, catalogues
  services/   business rules (certificate pipeline, verification cache, email)
  models/     SQLAlchemy models
  schemas/    Pydantic request / response contracts
  core/       config, security, CSRF, rate limiting, role dependencies
alembic/      11 versioned migrations (the schema is managed only by Alembic)
deploy/       nginx, systemd, docker-compose, scaling notes
tests/        pytest suite (28 tests)
```

Performance work for national-scale load includes composite and trigram indexes, N+1 fixes in the
certificate pipeline, a TTL cache on verification, and database statement timeouts. See
[`deploy/SCALE.md`](deploy/SCALE.md).

## Run locally

```bash
python -m venv venv && source venv/bin/activate   # Windows: .\venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env          # set DATABASE_URL and SECRET_KEY
alembic upgrade head
python seed.py                # creates the first admin; the password goes to a one-time file
python main.py
```

API: `http://localhost:8000/api/v1` · Docs: `http://localhost:8000/docs`

A local PostgreSQL instance is available through `deploy/docker-compose.yml`.

## Tests

```bash
pytest -q
```

The tests run on SQLite and cover authentication and logout revocation, the session lifecycle,
certificate issuing and verification, legacy imports, programmes and audit logging. CI runs them on every push.

## Deployment

- **Free staging** (Neon + Render + Vercel): [`deploy/FREE-DEPLOY.md`](deploy/FREE-DEPLOY.md)
- **Production** (Linux + Nginx + systemd + PostgreSQL 16): `deploy/` contains the nginx site, systemd unit,
  environment template and `deploy.sh`

## License

[MIT](LICENSE)
