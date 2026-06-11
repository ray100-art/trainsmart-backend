"""initial schema — all tables

Revision ID: 001_initial
Revises:
Create Date: 2026-05-25

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────────
    op.create_table('users',
        sa.Column('id',              sa.String(),               primary_key=True, nullable=False),
        sa.Column('username',        sa.String(),               nullable=False),
        sa.Column('email',           sa.String(),               nullable=False),
        sa.Column('hashed_password', sa.String(),               nullable=False),
        sa.Column('full_name',       sa.String(),               nullable=False),
        sa.Column('role',            sa.String(),               nullable=False),
        sa.Column('county',          sa.String(),               nullable=False),
        sa.Column('staff_number',    sa.String(),               nullable=True),
        sa.Column('is_active',       sa.Boolean(),              nullable=False, server_default=sa.true()),
        sa.Column('created_at',      sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',      sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_users_username',     'users', ['username'],     unique=True)
    op.create_index('ix_users_email',        'users', ['email'],        unique=True)
    op.create_index('ix_users_staff_number', 'users', ['staff_number'], unique=False)

    # ── training_sessions ──────────────────────────────────────────────────────
    op.create_table('training_sessions',
        sa.Column('id',                     sa.String(),               primary_key=True, nullable=False),
        sa.Column('title',                  sa.String(),               nullable=False),
        sa.Column('county',                 sa.String(),               nullable=False),
        sa.Column('facility',               sa.String(),               nullable=False),
        sa.Column('trainee_count',          sa.Integer(),              nullable=True,  server_default='0'),
        sa.Column('start_date',             sa.String(),               nullable=False),
        sa.Column('end_date',               sa.String(),               nullable=False),
        sa.Column('status',                 sa.String(),               nullable=True,  server_default='UPCOMING'),
        sa.Column('approval_status',        sa.String(),               nullable=True,  server_default='PENDING'),
        sa.Column('approval_note',          sa.Text(),                 nullable=True),
        sa.Column('approved_by',            sa.String(),               nullable=True),
        sa.Column('report_summary',         sa.Text(),                 nullable=True),
        sa.Column('report_challenges',      sa.Text(),                 nullable=True),
        sa.Column('report_recommendations', sa.Text(),                 nullable=True),
        sa.Column('report_submitted_at',    sa.String(),               nullable=True),
        sa.Column('report_approval_status', sa.String(),               nullable=True,  server_default='PENDING'),
        sa.Column('report_approval_note',   sa.Text(),                 nullable=True),
        sa.Column('certificates_issued',    sa.Boolean(),              nullable=True,  server_default=sa.false()),
        sa.Column('created_by',             sa.String(),               sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at',             sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at',             sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index('ix_training_sessions_county', 'training_sessions', ['county'], unique=False)

    # ── participants ───────────────────────────────────────────────────────────
    op.create_table('participants',
        sa.Column('id',                 sa.String(), primary_key=True, nullable=False),
        sa.Column('session_id',         sa.String(), sa.ForeignKey('training_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name',               sa.String(), nullable=False),
        sa.Column('staff_number',       sa.String(), nullable=True),
        sa.Column('cadre',              sa.String(), nullable=False),
        sa.Column('facility',           sa.String(), nullable=False),
        sa.Column('status',             sa.String(), nullable=True, server_default='PRESENT'),
        sa.Column('pre_test_score',     sa.Float(),  nullable=True),
        sa.Column('post_test_score',    sa.Float(),  nullable=True),
        sa.Column('certificate_serial', sa.String(), nullable=True, unique=True),
    )
    op.create_index('ix_participants_session_id',   'participants', ['session_id'],   unique=False)
    op.create_index('ix_participants_staff_number', 'participants', ['staff_number'], unique=False)

    # ── session_trainers ───────────────────────────────────────────────────────
    op.create_table('session_trainers',
        sa.Column('id',         sa.String(), primary_key=True, nullable=False),
        sa.Column('session_id', sa.String(), sa.ForeignKey('training_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name',       sa.String(), nullable=False),
        sa.Column('cadre',      sa.String(), nullable=False),
        sa.Column('phone',      sa.String(), nullable=False),
    )
    op.create_index('ix_session_trainers_session_id', 'session_trainers', ['session_id'], unique=False)


def downgrade() -> None:
    op.drop_table('session_trainers')
    op.drop_table('participants')
    op.drop_table('training_sessions')
    op.drop_table('users')