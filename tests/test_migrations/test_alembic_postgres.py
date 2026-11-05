"""End-to-end migration tests against a real Postgres instance.

Skipped automatically unless ``ODYSSEUS_MULTITENANT_POSTGRES=test`` and a
Postgres URL is reachable via ``DATABASE_URL``. This keeps the default
developer-macOS flow (SQLite + MagicMock httpx/fastapi) intact.

Run locally:
    docker run -d --name odysseus-pg-test -p 5432:5432 \\
        -e POSTGRES_PASSWORD=test -e POSTGRES_DB=test postgres:16
    DATABASE_URL=postgresql+psycopg://postgres:test@localhost:5432/test \\
    ODYSSEUS_MULTITENANT_POSTGRES=test pytest tests/test_migrations -v
"""
from __future__ import annotations

import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]


def _pg_enabled() -> bool:
    if os.getenv("ODYSSEUS_MULTITENANT_POSTGRES") != "test":
        return False
    url = os.getenv("DATABASE_URL", "")
    return "postgres" in url


pytestmark = pytest.mark.skipif(
    not _pg_enabled(),
    reason="Set ODYSSEUS_MULTITENANT_POSTGRES=test and DATABASE_URL=<postgres> to run",
)


def test_alembic_upgrade_head_applies_clean() -> None:
    """Stamping to head on an empty Postgres should succeed without errors."""
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect

    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)
    inspector = inspect(engine)
    # We start with no Odysseus tables; the schema_migrations row from a
    # previous test run is fine because Alembic is idempotent against it.
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")

    # Spot-check several critical tables from the baseline schema.
    tables = set(inspector.get_table_names())
    expected_subset = {
        "sessions",
        "chat_messages",
        "documents",
        "documents_version",
        "memories",
        "users",  # if it exists in models; harmless if not
    }
    found = expected_subset & tables
    assert {"sessions", "chat_messages", "documents"} <= found, (
        f"baseline missing critical tables; found={sorted(found)}"
    )


def test_alembic_round_trip() -> None:
    """Drop a table, re-run upgrade head, verify it returns.

    Confirms the baseline migration is genuinely idempotent and that
    missing tables get recreated on the next upgrade.
    """
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect, text

    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)

    # Drop a non-critical table; pick one without incoming FKs.
    target = "editor_drafts"
    with engine.begin() as conn:
        conn.execute(text(f'DROP TABLE IF EXISTS "{target}" CASCADE'))
    inspector = inspect(engine)
    assert target not in inspector.get_table_names()

    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    inspector = inspect(engine)
    assert target in inspector.get_table_names(), (
        f"upgrade head did not recreate {target}"
    )
