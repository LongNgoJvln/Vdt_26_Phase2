"""Initial schema baseline (mirrors core.database.Base.metadata).

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-08-18

This is the Alembic baseline for the multi-tenant Postgres backend. It is
the first migration that runs when ``ODYSSEUS_MULTITENANT_POSTGRES=true``
flips on. It uses ``Base.metadata.create_all`` against the migration
connection so the schema exactly matches what SQLAlchemy would have
produced under the legacy SQLite ``create_all`` path — every table, index,
foreign key, and ``EncryptedText`` column.

Going forward, schema changes are hand-authored migrations that use the
``op.create_table`` / ``op.add_column`` API so they diff cleanly against
this baseline.

Existing deploys that already have a Postgres schema (e.g. forked
deployments) should ``alembic stamp head`` instead of running this — it
records the revision as applied without re-issuing DDL.
"""
from alembic import op

from core.database import Base


revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())
