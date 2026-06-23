"""Security hardening: token_version, setup tokens, audit log

Revision ID: 003_security_hardening
Revises: 002_date_columns
Create Date: 2026-06-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '003_security_hardening'
down_revision: Union[str, None] = '002_date_columns'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('setup_token', sa.String(), nullable=True))
    op.add_column('users', sa.Column('setup_token_expires', sa.DateTime(timezone=True), nullable=True))

    op.create_table(
        'audit_logs',
        sa.Column('id', sa.String(), primary_key=True, nullable=False),
        sa.Column('user_id', sa.String(), nullable=True),
        sa.Column('action', sa.String(), nullable=False),
        sa.Column('entity_type', sa.String(), nullable=False),
        sa.Column('entity_id', sa.String(), nullable=True),
        sa.Column('detail', sa.Text(), nullable=True),
        sa.Column('ip_address', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_audit_logs_created_at', 'audit_logs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_audit_logs_created_at', table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_column('users', 'setup_token_expires')
    op.drop_column('users', 'setup_token')
    op.drop_column('users', 'token_version')
