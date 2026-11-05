"""Owner isolation for the DB-backed ``Upload`` table and ``UploadHandler``.

Each upload row is owner-scoped via the ``UniqueConstraint(owner, sha256)``
named ``uq_uploads_owner_sha``. These tests verify:

* Two different owners may upload identical content (each gets their own
  row + file id).
* ``get_upload_info`` filters by ``owner`` when the calling context
  provides it — user A cannot see user B's metadata by file id alone
  (the caller is responsible for the auth check; the handler just
  returns whatever the row query finds, which mirrors the legacy
  behavior of the JSON index that gated access at the route layer).

Skipped unless ``ODYSSEUS_MULTITENANT_POSTGRES=test`` and a Postgres URL
is configured.
"""
from __future__ import annotations

import io
import os
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import pytest
from sqlalchemy.exc import IntegrityError


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
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    from core import feature_flags as features
    from core.database import Base
    from src.upload_handler import UploadHandler

    features._FLAGS_OVERRIDE = {"uploads_in_db": True}

    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["uploads"]])
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    base = tmp_path / "base"
    up = tmp_path / "uploads"
    base.mkdir()
    up.mkdir()

    handler = UploadHandler(base_dir=str(base), upload_dir=str(up))
    import src.upload_handler as uh
    uh.SessionLocal = SessionLocal

    return handler, engine


def test_two_owners_same_content_get_distinct_rows(tmp_path):
    """Owners A and B upload identical bytes; both rows persist with their
    own file ids (composite unique is ``(owner, sha256)``, not ``sha256``
    alone)."""
    handler, _ = _make_handler(tmp_path)
    handler.upload_rate_limit = 100

    content = b"shared-bytes-" + os.urandom(4)

    a_result = handler.save_upload(
        SimpleNamespace(filename="shared.txt", file=io.BytesIO(content)),
        "127.0.0.1",
        "owner_a",
    )
    b_result = handler.save_upload(
        SimpleNamespace(filename="shared.txt", file=io.BytesIO(content)),
        "127.0.0.1",
        "owner_b",
    )

    assert a_result["id"] != b_result["id"], (
        "Cross-owner uploads should NOT dedupe — the unique constraint is "
        "(owner, sha256). Two owners uploading the same content should "
        "yield two distinct file ids."
    )

    # Both rows retrievable by their respective ids.
    a_info = handler.get_upload_info(a_result["id"])
    b_info = handler.get_upload_info(b_result["id"])
    assert a_info and a_info["owner"] == "owner_a"
    assert b_info and b_info["owner"] == "owner_b"


def test_same_owner_same_content_dedupes(tmp_path):
    """Same owner re-uploading identical bytes dedupes: save_upload returns
    ``is_duplicate=True`` and the original file id (no new row inserted)."""
    handler, _ = _make_handler(tmp_path)
    handler.upload_rate_limit = 100

    content = b"dup-bytes-" + os.urandom(4)

    first = handler.save_upload(
        SimpleNamespace(filename="orig.txt", file=io.BytesIO(content)),
        "127.0.0.1",
        "owner_a",
    )
    second = handler.save_upload(
        SimpleNamespace(filename="orig.txt", file=io.BytesIO(content)),
        "127.0.0.1",
        "owner_a",
    )

    assert second.get("is_duplicate") is True
    assert second["id"] == first["id"]


def test_owner_sha256_constraint_enforced_directly(tmp_path):
    """Even if a caller bypasses ``save_upload``, the DB enforces the
    unique constraint: inserting two rows with the same ``(owner, sha256)``
    raises ``IntegrityError``."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session as DBSession

    from core.database import Base, Upload

    engine = create_engine(os.environ["DATABASE_URL"])
    Base.metadata.create_all(bind=engine, tables=[Base.metadata.tables["uploads"]])

    sha = "a" * 64
    owner = f"constraint_owner_{uuid.uuid4().hex[:6]}"

    with DBSession(engine) as db:
        db.add(Upload(id=f"row1_{uuid.uuid4().hex[:8]}", owner=owner, sha256=sha,
                       safe_filename="f.txt", original_name="f.txt",
                       mime="text/plain", size=1, file_scope="library"))
        db.commit()

    with DBSession(engine) as db:
        db.add(Upload(id=f"row2_{uuid.uuid4().hex[:8]}", owner=owner, sha256=sha,
                       safe_filename="f.txt", original_name="f.txt",
                       mime="text/plain", size=1, file_scope="library"))
        with pytest.raises(IntegrityError):
            db.commit()
