"""Add ``uploads`` table (replaces ``uploads.json`` index).

Revision ID: 0003_uploads_table
Revises: 0002_email_tables
Create Date: 2026-08-18

The ``Upload`` model mirrors the per-entry shape that previously lived
in the flat JSON index at ``<upload_dir>/uploads.json``. The index was
thread-locked but global, which broke under multi-worker deploys and
leaked owner scope (the bypass readers at ``routes/upload_routes.py``
opened the file directly without the lock).

Owner-scoped dedup is enforced at the DB layer via
``UniqueConstraint(owner, sha256)`` — the same content hash may belong
to multiple owners, but a single owner cannot have two copies.
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_uploads_table"
down_revision = "0002_email_tables"
branch_labels = None
depends_on = None


def _table_exists(bind, name: str) -> bool:
    return name in sa.inspect(bind).get_table_names()


def upgrade() -> None:
    bind = op.get_bind()
    if _table_exists(bind, "uploads"):
        return

    op.create_table(
        "uploads",
        sa.Column("id", sa.String(), nullable=False),
        sa.Column("owner", sa.String(), nullable=True),
        sa.Column("file_scope", sa.String(length=10), nullable=False, server_default="library"),
        sa.Column("session_id", sa.String(), nullable=True),
        sa.Column("original_name", sa.String(), nullable=False),
        sa.Column("safe_filename", sa.String(), nullable=False),
        sa.Column("mime", sa.String(), nullable=False),
        sa.Column("size", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(length=64), nullable=False),
        sa.Column("client_ip", sa.String(), nullable=True),
        sa.Column("uploaded_at", sa.DateTime(), nullable=False),
        sa.Column("last_accessed", sa.DateTime(), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("minio_key", sa.String(length=1024), nullable=True),
        sa.Column("local_path", sa.String(length=1024), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("owner", "sha256", name="uq_uploads_owner_sha"),
    )
    op.create_index("ix_uploads_id", "uploads", ["id"])
    op.create_index("ix_uploads_owner", "uploads", ["owner"])
    op.create_index("ix_uploads_file_scope", "uploads", ["file_scope"])
    op.create_index("ix_uploads_session_id", "uploads", ["session_id"])
    op.create_index("ix_uploads_sha256", "uploads", ["sha256"])
    op.create_index("ix_uploads_uploaded_at", "uploads", ["uploaded_at"])
    op.create_index("ix_uploads_expires_at", "uploads", ["expires_at"])


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS uploads")
