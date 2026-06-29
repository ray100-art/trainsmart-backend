"""Add report_approved_by to training_sessions; add rate_limit_events table

Revision ID: 004_report_approver_and_ratelimit
Revises: 003_security_hardening
Create Date: 2026-06-24

Changes:
  - training_sessions.report_approved_by  (nullable String) — stores the user
    ID of whichever county officer approved or rejected the training report,
    matching the existing approved_by column used for session approval.

  - rate_limit_events table — PostgreSQL-backed rate-limit store used when
    RATE_LIMIT_STORAGE=database is set in .env. Allows rate limiting to
    survive server restarts and work correctly across multiple workers.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '004_report_approver_and_ratelimit'
down_revision: Union[str, None] = '003_security_hardening'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Track who approved/rejected the training report
    op.add_column(
        'training_sessions',
        sa.Column('report_approved_by', sa.String(), nullable=True),
    )

    # DB-backed rate limiting table
    op.create_table(
        'rate_limit_events',
        sa.Column('id',         sa.String(),                   primary_key=True, nullable=False),
        sa.Column('scope',      sa.String(),                   nullable=False),
        sa.Column('identifier', sa.String(),                   nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.func.now(), nullable=False),
    )
    op.create_index('ix_rle_scope_identifier', 'rate_limit_events', ['scope', 'identifier'])
    op.create_index('ix_rle_created_at',       'rate_limit_events', ['created_at'])


def downgrade() -> None:
    op.drop_index('ix_rle_created_at',       table_name='rate_limit_events')
    op.drop_index('ix_rle_scope_identifier', table_name='rate_limit_events')
    op.drop_table('rate_limit_events')
    op.drop_column('training_sessions', 'report_approved_by')
