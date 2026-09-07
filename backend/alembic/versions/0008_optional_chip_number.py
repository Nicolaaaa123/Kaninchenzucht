"""chip_number optional

Revision ID: 0008
Revises: 0007
Create Date: 2026-09-06
"""

from alembic import op
import sqlalchemy as sa

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("animals", "chip_number", existing_type=sa.String(length=60), nullable=True)


def downgrade() -> None:
    op.alter_column("animals", "chip_number", existing_type=sa.String(length=60), nullable=False)
