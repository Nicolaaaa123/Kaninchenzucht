"""stall pages, feed container, target date range

Revision ID: 0003
Revises: 0002
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "stall_pages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("label", sa.String(120), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.add_column("stalls", sa.Column("page_id", postgresql.UUID(as_uuid=True), nullable=True))
    op.create_foreign_key("fk_stalls_page_id", "stalls", "stall_pages", ["page_id"], ["id"])

    op.add_column("feeds", sa.Column("container_capacity_grams", sa.Float(), nullable=True))

    op.add_column("animals", sa.Column("target_date_end", sa.Date(), nullable=True))


def downgrade() -> None:
    op.drop_column("animals", "target_date_end")
    op.drop_column("feeds", "container_capacity_grams")
    op.drop_constraint("fk_stalls_page_id", "stalls", type_="foreignkey")
    op.drop_column("stalls", "page_id")
    op.drop_table("stall_pages")
