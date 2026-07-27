"""Add indexes for session list/filter performance at national scale.

Revision ID: 007_session_list_indexes
Revises: 006_training_programs
Create Date: 2026-07-27
"""
from alembic import op

revision = "007_session_list_indexes"
down_revision = "006_training_programs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_training_sessions_created_by", "training_sessions", ["created_by"])
    op.create_index("ix_training_sessions_created_at", "training_sessions", ["created_at"])
    op.create_index("ix_training_sessions_approval_status", "training_sessions", ["approval_status"])
    op.create_index(
        "ix_training_sessions_county_created",
        "training_sessions",
        ["county", "created_at"],
    )
    op.create_index(
        "ix_training_sessions_created_by_created",
        "training_sessions",
        ["created_by", "created_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_training_sessions_created_by_created", table_name="training_sessions")
    op.drop_index("ix_training_sessions_county_created", table_name="training_sessions")
    op.drop_index("ix_training_sessions_approval_status", table_name="training_sessions")
    op.drop_index("ix_training_sessions_created_at", table_name="training_sessions")
    op.drop_index("ix_training_sessions_created_by", table_name="training_sessions")
