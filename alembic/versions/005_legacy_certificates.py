"""Add legacy_certificates table for migrated TrainSMART v3/v4 data

Revision ID: 005_legacy_certificates
Revises: 004_report_approver_and_ratelimit
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '005_legacy_certificates'
down_revision: Union[str, None] = '004_report_approver_and_ratelimit'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'legacy_certificates',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('serial', sa.String(), nullable=False),
        sa.Column('participant_name', sa.String(), nullable=False),
        sa.Column('cadre', sa.String(), nullable=False),
        sa.Column('facility', sa.String(), nullable=False),
        sa.Column('course', sa.String(), nullable=False),
        sa.Column('county', sa.String(), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('post_test_score', sa.Float(), nullable=True),
        sa.Column('issued_date', sa.Date(), nullable=True),
        sa.Column('era', sa.String(), nullable=False),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_legacy_certificates_serial', 'legacy_certificates', ['serial'], unique=True)
    op.create_index('ix_legacy_certificates_county', 'legacy_certificates', ['county'], unique=False)
    op.create_index('ix_legacy_certificates_era', 'legacy_certificates', ['era'], unique=False)


def downgrade() -> None:
    op.drop_table('legacy_certificates')
