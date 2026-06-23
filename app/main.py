from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.database import get_db
from app.routers import auth, sessions, participants, trainers, certificates, stats

# Tables are managed exclusively by Alembic migrations.
# NEVER call Base.metadata.create_all() here — it conflicts with Alembic
# and silently skips columns added in later migrations.
# Run:  alembic upgrade head

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="National Healthcare Training Registry - NASCOP - MOH Kenya",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,   # reads ALLOWED_ORIGINS from .env
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(sessions.router,      prefix=PREFIX)
app.include_router(participants.router,  prefix=PREFIX)
app.include_router(trainers.router,      prefix=PREFIX)
app.include_router(certificates.router,  prefix=PREFIX)
app.include_router(stats.router,         prefix=PREFIX)


@app.get("/")
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs" if settings.docs_enabled else "disabled in production",
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "healthy"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "unhealthy", "detail": "Database unreachable"})
