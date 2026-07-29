"""Add MFA columns on users.

Revision ID: 011_mfa_columns
Revises: 010_scale_indexes
Create Date: 2026-07-29
"""
from alembic import op
import sqlalchemy as sa

revision = "011_mfa_columns"
down_revision = "010_scale_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("mfa_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.add_column("users", sa.Column("mfa_secret", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "mfa_secret")
    op.drop_column("users", "mfa_enabled")
