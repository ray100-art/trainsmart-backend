"""Add training_programs catalog and link sessions to programs

Revision ID: 006_training_programs
Revises: 005_legacy_certificates
Create Date: 2026-06-29
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '006_training_programs'
down_revision: Union[str, None] = '005_legacy_certificates'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'training_programs',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('code', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(), nullable=False),
        sa.Column('target_cadres', sa.String(), nullable=True),
        sa.Column('duration_days', sa.Integer(), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_training_programs_code', 'training_programs', ['code'], unique=True)
    op.create_index('ix_training_programs_category', 'training_programs', ['category'], unique=False)

    op.add_column('training_sessions', sa.Column('program_id', sa.String(), nullable=True))
    op.create_foreign_key(
        'fk_training_sessions_program_id',
        'training_sessions', 'training_programs',
        ['program_id'], ['id'],
        ondelete='SET NULL',
    )
    op.create_index('ix_training_sessions_program_id', 'training_sessions', ['program_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_training_sessions_program_id', table_name='training_sessions')
    op.drop_constraint('fk_training_sessions_program_id', 'training_sessions', type_='foreignkey')
    op.drop_column('training_sessions', 'program_id')
    op.drop_table('training_programs')
