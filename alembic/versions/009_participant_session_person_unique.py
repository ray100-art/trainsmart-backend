"""Unique (session_id, person_id) to prevent duplicate enrollments / certificates.

Revision ID: 009_participant_session_person_unique
Revises: 008_people_catalogs_session_fields
Create Date: 2026-07-27
"""
from alembic import op

revision = "009_participant_session_person_unique"
down_revision = "008_people_catalogs_session_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Drop any accidental duplicates before enforcing uniqueness (keep earliest row).
    op.execute(
        """
        DELETE FROM participants
        WHERE id IN (
            SELECT id FROM (
                SELECT id,
                       ROW_NUMBER() OVER (
                           PARTITION BY session_id, person_id
                           ORDER BY id
                       ) AS rn
                FROM participants
                WHERE person_id IS NOT NULL
            ) ranked
            WHERE rn > 1
        )
        """
    )
    op.create_unique_constraint(
        "uq_participants_session_person",
        "participants",
        ["session_id", "person_id"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_participants_session_person", "participants", type_="unique")
