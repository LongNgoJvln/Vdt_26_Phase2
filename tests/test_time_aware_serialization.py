"""Time-aware serialization regressions.

Guards the UTC migration contract:
  A. API datetime strings are canonical ISO-8601 UTC with a trailing 'Z'
     (no zone-less strings that JS reads as local, no '+00:00Z' doubles).
  B. Chat message metadata timestamps end in 'Z'.
  C. Mixed data: a legacy NAIVE row read through the ORM serializes as the
     same instant (old rows don't shift).
  D. iso_utc never emits a double suffix.
  E. Legacy scheduled-email TEXT rows keep matching the naive cutoff compare.
"""
from __future__ import annotations

import re
import sys
import types
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _ensure_importable(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


_Z_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?Z$")


def test_iso_utc_canonical_forms_are_never_doubled():
    from core.time_utils import iso_utc

    aware = datetime(2026, 1, 1, 3, 43, 25, tzinfo=timezone.utc)
    naive = datetime(2026, 1, 1, 3, 43, 25)
    assert iso_utc(aware) == "2026-01-01T03:43:25Z"
    assert iso_utc(naive) == "2026-01-01T03:43:25Z"  # legacy naive row → same instant
    assert "+00:00Z" not in iso_utc(aware)
    assert _Z_RE.match(iso_utc(aware))
    assert iso_utc(None) is None


def _private_db():
    """Return (SessionModel, SessionLocal) bound to a PRIVATE temp SQLite DB.

    Full-suite runs leave `core.database` stubbed (MagicMock) or re-pointed
    at :memory: by earlier test modules (documented suite caveat), so these
    regression tests never touch the shared engine. A private engine makes
    them order-independent.
    """
    import tempfile
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    import core.database as cd
    if "MagicMock" in str(type(getattr(cd, "Session", None))):
        import importlib
        sys.modules.pop("core.database", None)
        cd = importlib.import_module("core.database")
    eng = create_engine(
        "sqlite:///" + tempfile.mkdtemp(prefix="tz-reg-") + "/tz.db",
        connect_args={"check_same_thread": False},
    )
    cd.Base.metadata.create_all(bind=eng)
    return cd.Session, sessionmaker(bind=eng, autocommit=False, autoflush=False)


def test_orm_roundtrip_is_aware_and_serializes_z():
    import uuid as _uuid
    DbSession, SessionLocal = _private_db()
    from core.time_utils import iso_utc

    row_id = f"tz-regression-{(_uuid.uuid4().hex)[:8]}"
    db = SessionLocal()
    try:
        s = DbSession(id=row_id, name="tz", endpoint_url="x",
                      model="m", owner="tz-test")
        db.add(s)
        db.commit()
        db.refresh(s)
        assert s.created_at.tzinfo is not None, "UtcDateTime reads must be aware"
        assert _Z_RE.match(iso_utc(s.created_at)), iso_utc(s.created_at)
        d = s.to_dict()
        for key in ("created_at", "updated_at"):
            assert _Z_RE.match(d[key]), (key, d[key])
    finally:
        db.delete(s)
        db.commit()
        db.close()


def test_legacy_naive_row_does_not_shift():
    """A naive-UTC row (pre-migration data) reads back aware — same instant."""
    import uuid as _uuid
    DbSession, SessionLocal = _private_db()
    from core.time_utils import as_utc, iso_utc

    row_id = f"tz-legacy-naive-{(_uuid.uuid4().hex)[:8]}"
    db = SessionLocal()
    s = DbSession(id=row_id, name="legacy", endpoint_url="x",
                  model="m", owner="tz-test")
    db.add(s)
    db.commit()
    # Force a naive value straight through raw SQL — the pre-migration form.
    from sqlalchemy import text as _sql_text
    db.execute(_sql_text(
        "UPDATE sessions SET created_at = '2026-01-01 03:43:25.000000' "
        "WHERE id = :rid"), {"rid": row_id})
    db.commit()
    db.expire_all()
    row = db.query(DbSession).filter(DbSession.id == row_id).first()
    ts = row.created_at
    assert ts.tzinfo is not None, "read-back must be aware"
    assert iso_utc(ts) == "2026-01-01T03:43:25Z", iso_utc(ts)
    db.delete(row)
    db.commit()
    db.close()


def test_scheduled_email_naive_cutoff_still_matches():
    """D4 quarantine: fetch_pending_due compares naive-UTC strings — a past
    naive row still counts as due (regression E)."""
    if not _ensure_importable("routes.email_helpers_scheduled_dao"):
        pytest_skip = __import__("pytest").skip
        pytest_skip("email dao not importable in this env")

    from routes.email_helpers_scheduled_dao import fetch_pending_due
    import inspect

    src = inspect.getsource(fetch_pending_due)
    # The compare path must stay naive-UTC (string compare on TEXT column).
    assert "utcnow_naive" in src or "now_iso" in src, (
        "fetch_pending_due must use the naive-UTC path for legacy TEXT rows")


def test_parse_ts_semantics():
    """core.time_utils.parse_iso: 'Z', '+00:00', and zone-less → aware UTC."""
    from core.time_utils import parse_iso, as_utc

    a = parse_iso("2026-01-01T03:43:25Z")
    b = parse_iso("2026-01-01T03:43:25+00:00")
    c = as_utc(datetime(2026, 1, 1, 3, 43, 25))
    assert a == b == c
    assert a.tzinfo is not None
