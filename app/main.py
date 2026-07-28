import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.csrf import CsrfMiddleware
from app.database import get_db, engine
from app.routers import (
    auth, sessions, participants, trainers, certificates, stats, programs, audit,
    people, catalogs,
)

logger = logging.getLogger("trainsmart")

# Tables are managed exclusively by Alembic migrations.
# NEVER call Base.metadata.create_all() here — it conflicts with Alembic
# and silently skips columns added in later migrations.
# Run:  alembic upgrade head


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    yield
    engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="National Healthcare Training Registry - NASCOP - MOH Kenya",
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    lifespan=lifespan,
)

if settings.trusted_hosts_list:
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts_list)

# CSRF runs inside CORS so preflight still works; add after CORS (Starlette = last added runs first)
app.add_middleware(CsrfMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-CSRF-Token"],
    expose_headers=["X-CSRF-Token"],
)

PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(sessions.router,      prefix=PREFIX)
app.include_router(participants.router,  prefix=PREFIX)
app.include_router(trainers.router,      prefix=PREFIX)
app.include_router(certificates.router,  prefix=PREFIX)
app.include_router(stats.router,         prefix=PREFIX)
app.include_router(programs.router,      prefix=PREFIX)
app.include_router(audit.router,         prefix=PREFIX)
app.include_router(people.router,        prefix=PREFIX)
app.include_router(catalogs.facilities_router, prefix=PREFIX)
app.include_router(catalogs.sponsors_router,   prefix=PREFIX)


@app.get("/api/v1/moodle")
def moodle_info():
    """Legacy Moodle menu — returns configured LMS URL if set."""
    return {
        "enabled": bool(settings.MOODLE_URL),
        "url": settings.MOODLE_URL or None,
        "categories_path": "/course/index.php" if settings.MOODLE_URL else None,
        "courses_path": "/course/search.php" if settings.MOODLE_URL else None,
    }


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
    except Exception as exc:
        logger.exception("Health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "unhealthy", "detail": "Database unreachable"},
        )
