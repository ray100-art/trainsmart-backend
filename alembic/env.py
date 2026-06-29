from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool, text
from alembic import context

from app.core.config import settings
from app.database import Base

# Import all models so Alembic sees them
import app.models  # noqa: F401

config = context.config
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _ensure_alembic_version_column_width(connection) -> None:
    """Alembic revision IDs can exceed VARCHAR(32) on older PostgreSQL setups."""
    if connection.dialect.name != "postgresql":
        return
    connection.execute(text(
        "ALTER TABLE alembic_version "
        "ALTER COLUMN version_num TYPE VARCHAR(64)"
    ))


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        _ensure_alembic_version_column_width(connection)
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()