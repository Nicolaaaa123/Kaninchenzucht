"""multi-tenant auth: tenants, users, sessions; scope breeds/stalls/stall_pages/feeds/animals to a tenant

Revision ID: 0007
Revises: 0006
Create Date: 2026-08-24
"""

import secrets
import uuid

import bcrypt
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

_TENANT_SCOPED_TABLES = ["breeds", "stall_pages", "stalls", "feeds", "animals"]


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("username", sa.String(60), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(200), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=True),
        sa.Column("invite_code", sa.String(12), nullable=False, unique=True),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_users_username", "users", ["username"])
    op.create_table(
        "sessions",
        sa.Column("token", sa.String(64), primary_key=True),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
    )

    for table in _TENANT_SCOPED_TABLES:
        op.add_column(
            table, sa.Column("tenant_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tenants.id"), nullable=True)
        )
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])

    # Bootstrap: bisherige Daten gehören ab jetzt einem einzigen Zuchtbetrieb mit
    # einem einzigen Admin-Login. Passwort wird zufällig erzeugt und nur hier
    # ausgegeben (nicht im Code gespeichert) -- danach sofort ändern bzw. über
    # die Admin-Seite weitere Logins anlegen.
    conn = op.get_bind()
    bootstrap_tenant_id = uuid.uuid4()
    bootstrap_password = secrets.token_urlsafe(9)
    password_hash = bcrypt.hashpw(bootstrap_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    invite_code = secrets.token_hex(4).upper()

    conn.execute(
        sa.text("INSERT INTO tenants (id, name, created_at) VALUES (:id, :name, now())"),
        {"id": bootstrap_tenant_id, "name": "Zuchtbetrieb"},
    )
    conn.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, display_name, invite_code, is_admin, tenant_id, created_at) "
            "VALUES (:id, :username, :password_hash, :display_name, :invite_code, true, :tenant_id, now())"
        ),
        {
            "id": uuid.uuid4(),
            "username": "admin",
            "password_hash": password_hash,
            "display_name": "Admin",
            "invite_code": invite_code,
            "tenant_id": bootstrap_tenant_id,
        },
    )

    for table in _TENANT_SCOPED_TABLES:
        conn.execute(
            sa.text(f"UPDATE {table} SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
            {"tenant_id": bootstrap_tenant_id},
        )
        op.alter_column(table, "tenant_id", nullable=False)

    op.drop_constraint("breeds_name_key", "breeds", type_="unique")
    op.create_unique_constraint("uq_breed_tenant_name", "breeds", ["tenant_id", "name"])
    op.drop_constraint("animals_chip_number_key", "animals", type_="unique")
    op.create_unique_constraint("uq_animal_tenant_chip", "animals", ["tenant_id", "chip_number"])

    print("=" * 72)
    print("Bootstrap-Admin-Login angelegt:")
    print(f"  Benutzername: admin")
    print(f"  Passwort:     {bootstrap_password}")
    print(f"  Einlade-Code: {invite_code}")
    print("Bitte sofort einloggen und über die Admin-Seite echte Logins anlegen.")
    print("=" * 72)


def downgrade() -> None:
    op.drop_constraint("uq_animal_tenant_chip", "animals", type_="unique")
    op.create_unique_constraint("animals_chip_number_key", "animals", ["chip_number"])
    op.drop_constraint("uq_breed_tenant_name", "breeds", type_="unique")
    op.create_unique_constraint("breeds_name_key", "breeds", ["name"])

    for table in reversed(_TENANT_SCOPED_TABLES):
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")

    op.drop_table("sessions")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_table("users")
    op.drop_table("tenants")
