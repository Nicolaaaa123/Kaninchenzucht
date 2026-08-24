"""breed growth points

Revision ID: 0002
Revises: 0001
Create Date: 2026-08-23
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "breed_growth_points",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("breed_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("breeds.id"), nullable=False),
        sa.Column("age_weeks", sa.Integer(), nullable=False),
        sa.Column("weight_grams", sa.Integer(), nullable=False),
        sa.UniqueConstraint("breed_id", "age_weeks", name="uq_breed_growth_age"),
    )


def downgrade() -> None:
    op.drop_table("breed_growth_points")
