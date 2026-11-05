"""Add ``auth_sessions`` table (replaces ``data/sessions.json``).

Revision ID: 0004_auth_sessions_table
Revises: 0003_uploads_table
Create Date: 2026-08-18

The auth cookie path previously persisted every active session token in a
flat JSON file. The file was a single-writer RLock-guarded blob, global
across tenants, and read on every authenticated request. The DB row is
keyed by the 32-byte hex token; ``AuthManager`` keeps its in-memory dict
as a per-process hot cache and falls through to this row only when a
cookie arrives that the cache hasn't seen (cold start, post-restart).

The ``expiry`` column is epoch seconds — same unit the existing
``time.time()`` comparisons use, so the cache + DB codepaths agree.
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_auth_sessions_table"
down_revision = "0003_uploads_table"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "auth_sessions"):
        return

    op.create_table(
        "auth_sessions",
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("username", sa.String(), nullable=False),
        sa.Column("expiry", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("token"),
    )
    op.create_index("ix_auth_sessions_username", "auth_sessions", ["username"])
    op.create_index("ix_auth_sessions_expiry", "auth_sessions", ["expiry"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS auth_sessions")
