#!/usr/bin/env bash
# TrainSMART first-time / upgrade deployment on Linux
# Usage: ./deploy.sh /path/to/backend.env
set -euo pipefail

ENV_FILE="${1:-/etc/trainsmart/backend.env}"
BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing env file: $ENV_FILE"
  echo "Copy deploy/env.production.example and fill in secrets."
  exit 1
fi

export $(grep -v '^#' "$ENV_FILE" | xargs)

echo "==> Waiting for PostgreSQL..."
until python -c "
import os, sys
from sqlalchemy import create_engine, text
e = create_engine(os.environ['DATABASE_URL'])
with e.connect() as c:
    c.execute(text('SELECT 1'))
" 2>/dev/null; do
  sleep 2
done

echo "==> Running Alembic migrations..."
cd "$BACKEND_DIR"
alembic upgrade head

echo "==> Seeding admin + NHITC programs (idempotent)..."
python seed.py

echo "==> Deployment complete."
echo "    Health: curl -s http://127.0.0.1:8000/health"
