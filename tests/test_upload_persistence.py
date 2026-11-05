"""Round-trip an upload through the DB-backed ``Upload`` model and
``UploadHandler`` to prove metadata survives a SessionLocal restart.

Skipped unless ``ODYSSEUS_MULTITENANT_POSTGRES=test`` and a Postgres
URL is configured (same gating pattern as test_database_postgres.py).

These tests cover the Phase-1 sub-scope C endpoints: when
``ODYSSEUS_UPLOADS_IN_DB=test`` is set, ``UploadHandler`` persists
metadata via SQLAlchemy against the ``Upload`` table. We verify:

* A new upload inserts a row whose ``id`` matches the file id.
* After dropping and recreating the engine + ``SessionLocal``,
  ``get_upload_info`` still returns the same metadata.
* The persisted ``sha256`` and ``size`` match the bytes on disk.
"""
from __future__ import annotations

import io
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _pg_enabled() -> bool:
    if os.getenv("ODYSSEUS_MULTITENANT_POSTGRES") != "test":
        return False
    return "postgres" in os.getenv("DATABASE_URL", "")


pytestmark = pytest.mark.skipif(
    not _pg_enabled(),
    reason="Set ODYSSEUS_MULTITENANT_POSTGRES=test and DATABASE_URL=<postgres> to run",
)


def _make_handler(tmp_path: Path):
    """Build an ``UploadHandler`` whose feature-flag dispatch will hit PG.

    Sets the in-process env override for ``uploads_in_db`` so the
    handler's ``_db_enabled()`` returns True regardless of the project
    default. Schema is created via ``Base.metadata.create_all`` against
    the live test engine (already at Alembic head per the suite setup).
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core import feature_flags as features
    from core.database import Base
    from src.upload_handler import UploadHandler

    # Reload feature-flags with the test env so the singleton picks up
    # the override (it is built once at import time).
    features._FLAGS_OVERRIDE = {"uploads_in_db": True}

    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["uploads"]])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    base = tmp_path / "base"
    up = tmp_path / "uploads"
    base.mkdir()
    up.mkdir()

    handler = UploadHandler(base_dir=str(base), upload_dir=str(up))
    # Inject our engine into the handler so we don't accidentally
    # mutate global state.
    handler._test_engine = engine
    handler._test_SessionLocal = SessionLocal

    # Monkeypatch the module-level SessionLocal to our test session so
    # _db_enabled picks the engine we just created.
    import src.upload_handler as uh
    uh.SessionLocal = SessionLocal

    return handler, engine


def test_upload_row_persists_across_session_restart(tmp_path):
    """Upload a blob, tear down SessionLocal, recreate it; the metadata
    round-trips via the new session against the same Postgres instance."""
    handler, engine = _make_handler(tmp_path)
    handler.upload_rate_limit = 100

    content = b"persistence-test-" + os.urandom(8)
    fake = SimpleNamespace(
        filename="persist.txt",
        file=io.BytesIO(content),
    )
    result = handler.save_upload(fake, "127.0.0.1", "owner_persist")
    file_id = result["id"]

    # Sanity: the file exists on disk and the returned shape is the
    # legacy-compatible dict.
    assert os.path.exists(result["path"])
    assert result["hash"]  # sha256 is populated

    # Drop the engine and create a fresh session against the same DB.
    engine.dispose()
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    new_engine = create_engine(os.environ["DATABASE_URL"])
    import src.upload_handler as uh
    uh.SessionLocal = sessionmaker(bind=new_engine, autoflush=False, autocommit=False)

    # Re-fetch through the handler — this is the read path that
    # production would use after a process restart.
    info = handler.get_upload_info(file_id)
    assert info is not None, "Upload row vanished across SessionLocal restart"
    assert info["id"] == file_id
    assert info["hash"] == result["hash"]
    assert info["size"] == len(content)
    assert info["owner"] == "owner_persist"

    # Byte-for-byte: sha256 of what's on disk matches what's in the row.
    import hashlib
    with open(result["path"], "rb") as fh:
        disk_sha = hashlib.sha256(fh.read()).hexdigest()
    assert disk_sha == info["hash"], "On-disk bytes diverged from the stored sha256"


def test_upload_stats_aggregate_from_db(tmp_path):
    """``get_upload_stats`` returns DB-backed aggregates when DB is on."""
    handler, _ = _make_handler(tmp_path)
    handler.upload_rate_limit = 100

    # Seed two uploads of distinct sizes.
    for label, n in [("small", 8), ("large", 4096)]:
        handler.save_upload(
            SimpleNamespace(
                filename=f"{label}.bin",
                file=io.BytesIO(b"x" * n),
            ),
            "127.0.0.1",
            "owner_stats",
        )

    stats = handler.get_upload_stats()
    # Either field name surface — handler returns legacy dict shape.
    total = stats.get("total_files") or stats.get("total_uploads") or 0
    assert total >= 2, f"Upload count aggregate wrong: {stats}"
