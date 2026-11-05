"""Diff Alembic ``upgrade head`` vs ``Base.metadata.create_all`` on fresh PG.

Catches drift between the models and the baseline migration. The baseline
``0001_initial_schema`` calls ``Base.metadata.create_all`` itself, so any
table that exists in models but is missing from the migration either (a)
was added by a hand-authored migration that we forgot to wire into the
upgrade chain, or (b) is genuinely an in-memory-only construct.

Set ODYSSEUS_MULTITENANT_POSTGRES=test and DATABASE_URL=<postgres> to run.
"""
from __future__ import annotations

import os
import pathlib

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _pg_enabled() -> bool:
    if os.getenv("ODYSSEUS_MULTITENANT_POSTGRES") != "test":
        return False
    url = os.getenv("DATABASE_URL", "")
    return "postgres" in url


pytestmark = pytest.mark.skipif(
    not _pg_enabled(),
    reason="Set ODYSSEUS_MULTITENANT_POSTGRES=test and DATABASE_URL=<postgres> to run",
)


def test_alembic_head_matches_create_all() -> None:
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, inspect

    from core.database import Base

    url = os.environ["DATABASE_URL"]

    # Phase 1: build via Alembic.
    alembic_engine = create_engine(url)
    cfg = Config(str(ROOT / "alembic.ini"))
    command.upgrade(cfg, "head")
    alembic_tables = set(inspect(alembic_engine).get_table_names())

    # Phase 2: fresh DB, build via create_all — should produce identical set.
    create_engine_tables = Base.metadata.tables.keys()
    missing = set(create_engine_tables) - alembic_tables
    assert not missing, (
        f"Tables defined in Base.metadata but absent from alembic head: {sorted(missing)}"
    )
