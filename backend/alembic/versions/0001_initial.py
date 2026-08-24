"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

# Stored as VARCHAR + CHECK constraint (native_enum=False) rather than a
# native Postgres ENUM type, to avoid driver-specific enum (de)serialization
# quirks (psycopg3 maps Python Enums by name, not by value, for native types).
sex_type = sa.Enum("male", "female", "unknown", name="sex", native_enum=False, length=20)
status_type = sa.Enum(
    "active", "sold", "deceased", "retired", name="animal_status", native_enum=False, length=20
)
breed_group_type = sa.Enum(
    "dwarf", "small", "medium", "large", name="breed_group", native_enum=False, length=20
)
feeding_stage_type = sa.Enum(
    "maintenance", "growth", "gestation", "lactation", name="feeding_stage", native_enum=False, length=20
)


def upgrade() -> None:
    op.create_table(
        "breeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False, unique=True),
        sa.Column("abbreviation", sa.String(20), nullable=True),
        sa.Column("group", breed_group_type, nullable=True),
        sa.Column("min_weight_kg", sa.Float(), nullable=True),
        sa.Column("ideal_weight_min_kg", sa.Float(), nullable=True),
        sa.Column("ideal_weight_max_kg", sa.Float(), nullable=True),
        sa.Column("max_weight_kg", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "breed_scoring_positions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("breed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("breeds.id"), nullable=False),
        sa.Column("position_number", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("max_points", sa.Integer(), nullable=False),
        sa.UniqueConstraint("breed_id", "position_number", name="uq_breed_position"),
    )

    op.create_table(
        "stalls",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("rows", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("columns", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "cage_boxes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("stall_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("stalls.id"), nullable=False),
        sa.Column("row_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("col_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("label", sa.String(60), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stall_id", "row_index", "col_index", name="uq_stall_grid_position"),
    )

    op.create_table(
        "feeds",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("manufacturer", sa.String(120), nullable=True),
        sa.Column("energy_mj_per_kg", sa.Float(), nullable=False),
        sa.Column("crude_protein_pct", sa.Float(), nullable=True),
        sa.Column("crude_fiber_pct", sa.Float(), nullable=True),
        sa.Column("crude_fat_pct", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "animals",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("chip_number", sa.String(60), nullable=False, unique=True),
        sa.Column("tattoo_number", sa.String(60), nullable=True),
        sa.Column("name", sa.String(120), nullable=True),
        sa.Column("sex", sex_type, nullable=False, server_default="unknown"),
        sa.Column("birth_date", sa.Date(), nullable=True),
        sa.Column("status", status_type, nullable=False, server_default="active"),
        sa.Column("color_variant", sa.String(120), nullable=True),
        sa.Column("feeding_stage", feeding_stage_type, nullable=False, server_default="maintenance"),
        sa.Column("target_weight_grams", sa.Integer(), nullable=True),
        sa.Column("target_date", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("breed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("breeds.id"), nullable=True),
        sa.Column("cage_box_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("cage_boxes.id"), nullable=True),
        sa.Column("feed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("feeds.id"), nullable=True),
        sa.Column("mother_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("animals.id"), nullable=True),
        sa.Column("father_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("animals.id"), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_animals_chip_number", "animals", ["chip_number"])

    op.create_table(
        "weight_entries",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("animal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("measured_on", sa.Date(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("animal_id", "measured_on", name="uq_weight_animal_date"),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("animal_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("animals.id"), nullable=False),
        sa.Column("evaluated_on", sa.Date(), nullable=False),
        sa.Column("show_name", sa.String(200), nullable=True),
        sa.Column("exhibitor_number", sa.String(60), nullable=True),
        sa.Column("exhibitor_name", sa.String(200), nullable=True),
        sa.Column("exhibitor_address", sa.String(300), nullable=True),
        sa.Column("total_score", sa.Float(), nullable=True),
        sa.Column("weight_grams", sa.Integer(), nullable=True),
        sa.Column("photo_path", sa.String(500), nullable=True),
        sa.Column("source", sa.String(20), nullable=False, server_default="manual"),
        sa.Column("confirmed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    op.create_table(
        "evaluation_scores",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "evaluation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("evaluations.id"), nullable=False
        ),
        sa.Column("position_number", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("category_label", sa.String(120), nullable=False),
        sa.Column("max_points", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("points", sa.Float(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("evaluation_scores")
    op.drop_table("evaluations")
    op.drop_table("weight_entries")
    op.drop_index("ix_animals_chip_number", table_name="animals")
    op.drop_table("animals")
    op.drop_table("feeds")
    op.drop_table("cage_boxes")
    op.drop_table("stalls")
    op.drop_table("breed_scoring_positions")
    op.drop_table("breeds")
