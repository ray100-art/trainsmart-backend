from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from app.core.config import settings

_is_sqlite = settings.DATABASE_URL.startswith("sqlite")

connect_args = {"check_same_thread": False} if _is_sqlite else {}

# SQLite doesn't support connection pooling options; PostgreSQL does.
_pool_kwargs = (
    {}
    if _is_sqlite
    else {
        "pool_size":     settings.DB_POOL_SIZE,
        "max_overflow":  settings.DB_MAX_OVERFLOW,
        "pool_recycle":  settings.DB_POOL_RECYCLE,
        "pool_timeout":  30,
    }
)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=connect_args,
    pool_pre_ping=True,
    **_pool_kwargs,
)

if not _is_sqlite:
    @event.listens_for(engine, "connect")
    def _set_pg_timeouts(dbapi_conn, _connection_record):
        # Kill runaway queries; protects the pool under national load
        cursor = dbapi_conn.cursor()
        try:
            cursor.execute("SET statement_timeout = '15000'")  # 15s
            cursor.execute("SET idle_in_transaction_session_timeout = '30000'")  # 30s
        finally:
            cursor.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db: Session = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
