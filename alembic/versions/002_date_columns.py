"""Change date/timestamp String columns to native Date type

Revision ID: 002_date_columns
Revises: 001_initial
Create Date: 2026-06-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_date_columns'
down_revision: Union[str, None] = '001_initial'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table('training_sessions') as batch_op:
        batch_op.alter_column(
            'start_date',
            existing_type=sa.String(),
            type_=sa.Date(),
            postgresql_using='start_date::date',
            nullable=False,
        )
        batch_op.alter_column(
            'end_date',
            existing_type=sa.String(),
            type_=sa.Date(),
            postgresql_using='end_date::date',
            nullable=False,
        )
        batch_op.alter_column(
            'report_submitted_at',
            existing_type=sa.String(),
            type_=sa.Date(),
            postgresql_using='report_submitted_at::date',
            nullable=True,
        )


def downgrade() -> None:
    with op.batch_alter_table('training_sessions') as batch_op:
        batch_op.alter_column(
            'start_date',
            existing_type=sa.Date(),
            type_=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            'end_date',
            existing_type=sa.Date(),
            type_=sa.String(),
            nullable=False,
        )
        batch_op.alter_column(
            'report_submitted_at',
            existing_type=sa.Date(),
            type_=sa.String(),
            nullable=True,
        )
