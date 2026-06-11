from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.routers import auth, sessions, participants, trainers, certificates

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
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

PREFIX = "/api/v1"
app.include_router(auth.router,          prefix=PREFIX)
app.include_router(sessions.router,      prefix=PREFIX)
app.include_router(participants.router,  prefix=PREFIX)
app.include_router(trainers.router,      prefix=PREFIX)
app.include_router(certificates.router,  prefix=PREFIX)


@app.get("/")
def root():
    return {
        "app":     settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status":  "running",
        "docs":    "/docs" if settings.docs_enabled else "disabled in production",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}