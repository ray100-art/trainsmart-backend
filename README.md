# TrainSMART Backend

FastAPI + PostgreSQL API for NASCOP/MOH Kenya national training registry.

## Development

```powershell
cd C:\transmart-backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Edit .env — set DATABASE_URL to your PostgreSQL instance
alembic upgrade head
python seed.py
python main.py
```

API: http://localhost:8000  
Docs: http://localhost:8000/docs (disabled when `ENVIRONMENT=production`)

## PostgreSQL

Development and production both use PostgreSQL. Example `DATABASE_URL`:

```
postgresql://postgres:password@localhost:5432/trainsmart
```

Local Postgres via Docker:

```powershell
cd deploy
$env:POSTGRES_PASSWORD="yourpassword"
docker compose up -d
```

Then set `DATABASE_URL=postgresql://trainsmart:yourpassword@localhost:5432/trainsmart`.

## Production deployment

See `deploy/` for:

| File | Purpose |
|------|---------|
| `env.production.example` | Production environment template |
| `docker-compose.yml` | PostgreSQL 16 container |
| `nginx-trainsmart.conf` | Nginx reverse proxy + SPA |
| `trainsmart-api.service` | systemd unit (4 Uvicorn workers) |
| `deploy.sh` | Migrate + seed on Linux |

### Production checklist

1. Provision PostgreSQL 16 (managed or `docker compose` in `deploy/`)
2. Copy `deploy/env.production.example` → `/etc/trainsmart/backend.env`
3. Set `ENVIRONMENT=production`, strong `SECRET_KEY`, real `DATABASE_URL`
4. `alembic upgrade head` && `python seed.py`
5. Build frontend with `VITE_API_URL=/api/v1` (same-origin) or full API URL
6. Deploy `dist/` to `/var/www/trainsmart/frontend/dist`
7. Enable nginx site + SSL (Let's Encrypt or MOH PKI)
8. Enable `trainsmart-api.service`

### Frontend pairing

Canonical frontend: `C:\trainsmart-frontend`  
Production build: `npm run build` with `.env.production` from `.env.production.example`

## Tests

```powershell
pytest tests/ -q
```

Uses SQLite test DB only in tests — production requires PostgreSQL.
