"""claws trimmed on

Revision ID: 0010
Revises: 0009
Create Date: 2026-10-15
"""

from alembic import op
import sqlalchemy as sa

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("animals", sa.Column("claws_trimmed_on", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("animals", "claws_trimmed_on")
