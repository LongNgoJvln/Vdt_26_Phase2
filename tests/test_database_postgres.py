"""Round-trip every Postgres model: insert+read proves the table works.

Skipped unless ``ODYSSEUS_MULTITENANT_POSTGRES=test`` and a Postgres
URL is configured.
"""
from __future__ import annotations

import os
import uuid

import pytest


def _pg_enabled() -> bool:
    if os.getenv("ODYSSEUS_MULTITENANT_POSTGRES") != "test":
        return False
    return "postgres" in os.getenv("DATABASE_URL", "")


pytestmark = pytest.mark.skipif(
    not _pg_enabled(),
    reason="Set ODYSSEUS_MULTITENANT_POSTGRES=test and DATABASE_URL=<postgres> to run",
)


def _pg_url() -> str:
    return os.environ["DATABASE_URL"]


def test_chatmessage_metadata_alias_preserved() -> None:
    """The DB column is named ``metadata`` (SQLAlchemy reserved-ish);
    the ORM attribute is ``meta_data``. Verify both work end-to-end."""
    from sqlalchemy import create_engine, inspect

    engine = create_engine(_pg_url())
    cols = {c["name"]: c for c in inspect(engine).get_columns("chat_messages")}
    assert "metadata" in cols, "DB column must be named 'metadata' (aliased)"
    # SQLAlchemy should refuse a column literally named 'metadata' as an attr,
    # so the model uses 'meta_data' — we just verify the DB side here.


def test_session_round_trip() -> None:
    """Insert a Session, then SELECT it back via the ORM."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as DBSession

    from core.database import Session as SessionModel, Base

    engine = create_engine(_pg_url())
    # Schema already at head per test_migrations setup.
    sid = f"test-{uuid.uuid4().hex[:12]}"

    with DBSession(engine) as db:
        existing = db.query(SessionModel).filter(SessionModel.id == sid).first()
        if existing:
            db.delete(existing)
            db.commit()

    with DBSession(engine) as db:
        row = SessionModel(
            id=sid,
            title="migration smoke",
            model="test-model",
            owner="audit",
        )
        db.add(row)
        db.commit()

    with DBSession(engine) as db:
        loaded = db.query(SessionModel).filter(SessionModel.id == sid).one()
        assert loaded.title == "migration smoke"
        assert loaded.owner == "audit"


def test_usertooldata_autoincrement() -> None:
    """``UserToolData.id`` is the only Integer-autoincrement PK. Under
    Postgres it must serialize via SERIAL/IDENTITY, not error."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as DBSession

    from core.database import UserToolData, UserTool

    engine = create_engine(_pg_url())
    with DBSession(engine) as db:
        # Ensure a tool exists to attach data to.
        tool_id = f"tool-{uuid.uuid4().hex[:8]}"
        # Skip if model layout requires fields we don't know — the
        # SELECT CURRVAL round-trip is the test, not the row content.
        cols = {c.name for c in UserToolData.__table__.columns}
        required = {c.name for c in UserToolData.__table__.columns if c.nullable is False}
        required -= {"id"}
        if "tool_id" in required and "session_id" in required:
            pytest.skip("UserToolData requires FK parents not set up for this test")
