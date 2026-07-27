"""Add people registry, facility/sponsor catalogs, and legacy training fields.

Revision ID: 008_people_catalogs_session_fields
Revises: 007_session_list_indexes
Create Date: 2026-07-27
"""
from alembic import op
import sqlalchemy as sa

revision = "008_people_catalogs_session_fields"
down_revision = "007_session_list_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "people",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("national_id", sa.String(), nullable=False),
        sa.Column("first_name", sa.String(), nullable=False),
        sa.Column("middle_name", sa.String(), nullable=True),
        sa.Column("last_name", sa.String(), nullable=False),
        sa.Column("gender", sa.String(), nullable=False),
        sa.Column("qualification", sa.String(), nullable=False),
        sa.Column("facility", sa.String(), nullable=False),
        sa.Column("county", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_by", sa.String(), sa.ForeignKey("users.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_people_national_id", "people", ["national_id"], unique=True)
    op.create_index("ix_people_county", "people", ["county"])
    op.create_index("ix_people_name", "people", ["last_name", "first_name"])
    op.create_index("ix_people_county_facility", "people", ["county", "facility"])

    op.create_table(
        "facilities",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("county", sa.String(), nullable=False),
        sa.Column("mfl_code", sa.String(), nullable=True),
        sa.Column("facility_type", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_facilities_name", "facilities", ["name"])
    op.create_index("ix_facilities_county", "facilities", ["county"])
    op.create_index("ix_facilities_mfl_code", "facilities", ["mfl_code"], unique=True)

    op.create_table(
        "sponsors",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("code", sa.String(), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_sponsors_name", "sponsors", ["name"], unique=True)
    op.create_index("ix_sponsors_code", "sponsors", ["code"], unique=True)

    op.add_column("training_sessions", sa.Column("funding_source", sa.String(), nullable=True))
    op.add_column("training_sessions", sa.Column("venue", sa.String(), nullable=True))
    op.add_column(
        "training_sessions",
        sa.Column("sponsor_id", sa.String(), sa.ForeignKey("sponsors.id", ondelete="SET NULL"), nullable=True),
    )
    op.add_column(
        "training_sessions",
        sa.Column("certificates_signed", sa.Boolean(), nullable=False, server_default=sa.text("false")),
    )
    op.create_index("ix_training_sessions_sponsor_id", "training_sessions", ["sponsor_id"])

    op.add_column(
        "participants",
        sa.Column("person_id", sa.String(), sa.ForeignKey("people.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_participants_person_id", "participants", ["person_id"])


def downgrade() -> None:
    op.drop_index("ix_participants_person_id", table_name="participants")
    op.drop_column("participants", "person_id")

    op.drop_index("ix_training_sessions_sponsor_id", table_name="training_sessions")
    op.drop_column("training_sessions", "certificates_signed")
    op.drop_column("training_sessions", "sponsor_id")
    op.drop_column("training_sessions", "venue")
    op.drop_column("training_sessions", "funding_source")

    op.drop_index("ix_sponsors_code", table_name="sponsors")
    op.drop_index("ix_sponsors_name", table_name="sponsors")
    op.drop_table("sponsors")

    op.drop_index("ix_facilities_mfl_code", table_name="facilities")
    op.drop_index("ix_facilities_county", table_name="facilities")
    op.drop_index("ix_facilities_name", table_name="facilities")
    op.drop_table("facilities")

    op.drop_index("ix_people_county_facility", table_name="people")
    op.drop_index("ix_people_name", table_name="people")
    op.drop_index("ix_people_county", table_name="people")
    op.drop_index("ix_people_national_id", table_name="people")
    op.drop_table("people")
