"""breeding category, delete cascades for parent/box links

Revision ID: 0004
Revises: 0003
Create Date: 2026-08-24
"""

from alembic import op
import sqlalchemy as sa

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "animals",
        sa.Column(
            "category",
            sa.String(length=20),
            nullable=False,
            server_default="young",
        ),
    )
    op.create_check_constraint(
        "breeding_category", "animals", "category IN ('young', 'breeding', 'external')"
    )

    op.drop_constraint("animals_mother_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key(
        "animals_mother_id_fkey", "animals", "animals", ["mother_id"], ["id"], ondelete="SET NULL"
    )
    op.drop_constraint("animals_father_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key(
        "animals_father_id_fkey", "animals", "animals", ["father_id"], ["id"], ondelete="SET NULL"
    )
    op.drop_constraint("animals_cage_box_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key(
        "animals_cage_box_id_fkey", "animals", "cage_boxes", ["cage_box_id"], ["id"], ondelete="SET NULL"
    )


def downgrade() -> None:
    op.drop_constraint("animals_cage_box_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key("animals_cage_box_id_fkey", "animals", "cage_boxes", ["cage_box_id"], ["id"])
    op.drop_constraint("animals_father_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key("animals_father_id_fkey", "animals", "animals", ["father_id"], ["id"])
    op.drop_constraint("animals_mother_id_fkey", "animals", type_="foreignkey")
    op.create_foreign_key("animals_mother_id_fkey", "animals", "animals", ["mother_id"], ["id"])

    op.drop_constraint("breeding_category", "animals", type_="check")
    op.drop_column("animals", "category")
