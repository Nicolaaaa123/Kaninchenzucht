"""ai usage limits: per-login monthly quota for scans / chat + usage log

Revision ID: 0011
Revises: 0010
Create Date: 2026-10-16
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # NULL = unbegrenzt -- bestehende Logins behalten damit ihr bisheriges Verhalten.
    op.add_column("users", sa.Column("scan_limit", sa.Integer(), nullable=True))
    op.add_column("users", sa.Column("chat_limit", sa.Integer(), nullable=True))
    op.create_table(
        "usage_events",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(20), nullable=False),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_usage_events_user_created", "usage_events", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_usage_events_user_created", table_name="usage_events")
    op.drop_table("usage_events")
    op.drop_column("users", "chat_limit")
    op.drop_column("users", "scan_limit")
