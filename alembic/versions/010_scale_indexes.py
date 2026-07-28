"""Scale indexes for national people registry and certificate pipeline.

Revision ID: 010_scale_indexes
Revises: 009_participant_session_person_unique
Create Date: 2026-07-28
"""
from alembic import op

revision = "010_scale_indexes"
down_revision = "009_participant_session_person_unique"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # People list filters: active + county are on every national/county query
    op.create_index(
        "ix_people_county_active_name",
        "people",
        ["county", "is_active", "last_name", "first_name"],
    )
    op.create_index("ix_people_is_active", "people", ["is_active"])

    # Certificate pipeline / session status filters
    op.create_index(
        "ix_sessions_report_cert_pipeline",
        "training_sessions",
        ["report_approval_status", "certificates_issued", "certificates_signed", "end_date"],
    )
    op.create_index("ix_training_sessions_status", "training_sessions", ["status"])
    op.create_index("ix_training_sessions_end_date", "training_sessions", ["end_date"])

    # Rate-limit hot path: (scope, identifier, created_at)
    op.create_index(
        "ix_rle_scope_identifier_created",
        "rate_limit_events",
        ["scope", "identifier", "created_at"],
    )

    # Optional trigram search (skip quietly if extension is not permitted)
    try:
        op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_people_name_trgm "
            "ON people USING gin ((first_name || ' ' || last_name) gin_trgm_ops)"
        )
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_people_national_id_trgm "
            "ON people USING gin (national_id gin_trgm_ops)"
        )
    except Exception:
        pass


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_people_national_id_trgm")
    op.execute("DROP INDEX IF EXISTS ix_people_name_trgm")
    op.drop_index("ix_rle_scope_identifier_created", table_name="rate_limit_events")
    op.drop_index("ix_training_sessions_end_date", table_name="training_sessions")
    op.drop_index("ix_training_sessions_status", table_name="training_sessions")
    op.drop_index("ix_sessions_report_cert_pipeline", table_name="training_sessions")
    op.drop_index("ix_people_is_active", table_name="people")
    op.drop_index("ix_people_county_active_name", table_name="people")
