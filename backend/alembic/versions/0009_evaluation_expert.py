"""evaluation expert

Revision ID: 0009
Revises: 0008
Create Date: 2026-10-13
"""

from alembic import op
import sqlalchemy as sa

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("evaluations", sa.Column("expert_name", sa.String(length=300), nullable=True))


def downgrade() -> None:
    op.drop_column("evaluations", "expert_name")
