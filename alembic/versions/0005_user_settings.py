"""Add ``user_settings`` table (replaces ``data/user_prefs.json`` per-user block).

Revision ID: 0005_user_settings
Revises: 0004_auth_sessions_table
Create Date: 2026-08-18

The per-user preferences file was a single-writer JSON blob keyed by
username; every per-key update rewrote the entire file, and rows from
all users lived in one physical object. The DB row is keyed by
``(owner, key)`` so individual updates are O(1) and tenant data is
physically separated by row rather than by JSON nesting.

``value_json`` is intentionally TEXT (not native JSON / JSONB) so the
table is portable across SQLite and Postgres during the dual-write
window — the application layer already (de)serializes via
``json.dumps`` / ``json.loads`` on its hot path.
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_user_settings"
down_revision = "0004_auth_sessions_table"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "user_settings"):
        return

    op.create_table(
        "user_settings",
        sa.Column("owner", sa.String(), nullable=False),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value_json", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("owner", "key", name="pk_user_settings_owner_key"),
    )
    op.create_index("ix_user_settings_owner", "user_settings", ["owner"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS user_settings")
