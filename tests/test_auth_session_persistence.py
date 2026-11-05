"""Tests for DB-backed auth session persistence.

These cover the D.3 dispatch path in ``core.auth.AuthManager``:

* Tokens created via ``create_session`` land in the DB row store
  (keyed by token, owner recorded as username).
* A new process (cache drain) rehydrates the in-memory dict from DB.
* ``validate_token`` / ``get_username_for_token`` still work post-restart.
* ``revoke_token`` and ``revoke_user_sessions`` clear DB rows, not
  just the in-memory cache (a restart never brings them back).
* ``delete_user`` sweeps the user's DB rows so their cookie stops
  authenticating.

There is no real Postgres fixture here — the test stubs out
``core.database.AuthSession`` + ``SessionLocal`` and
``core.db_upsert`` so the AuthManager code paths run end-to-end
against an in-memory list. ``test_database_postgres.py`` covers the
row-level truth for the model against a live PG.
"""
from __future__ import annotations

import sys
import types
import time
from datetime import datetime
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_db_stubs(monkeypatch):
    """Create in-memory AuthSession row store and patch only the parts
    of ``core.database`` / ``core.db_upsert`` AuthManager uses. The real
    ``core.database`` module is preserved — just ``AuthSession`` and
    ``SessionLocal`` get swapped."""
    rows: dict[str, dict] = {}

    class _Column:
        """SQLAlchemy column stand-in: comparison operators record the
        filter clause so ``_Query.filter`` can replay it as a string."""

        def __init__(self, name: str):
            self._name = name

        def __eq__(self, other):
            return _Clause(self._name, "==", other)

        def __ne__(self, other):
            return _Clause(self._name, "!=", other)

        def __gt__(self, other):
            return _Clause(self._name, ">", other)

        def __hash__(self):
            return hash(self._name)

    class _Clause:
        def __init__(self, name: str, op: str, value):
            self.name = name
            self.op = op
            self.value = value

    class _AuthSessionRow:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _AuthSessionMeta(type):
        """Metaclass so class attribute access on ``AuthSession.token``
        / ``.username`` / ``.expiry`` returns a fresh ``_Column`` proxy
        per name (mimicking SQLAlchemy InstrumentedAttribute)."""
        def __getattr__(cls, name):
            # Real attributes (``__table__`` etc.) fall through; only
            # column names get a proxy.
            if name.startswith("__"):
                raise AttributeError(name)
            return _Column(name)

    class _AuthSessionCls(metaclass=_AuthSessionMeta):
        __tablename__ = "auth_sessions"

        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Query:
        def __init__(self, rows_ref):
            self._rows = rows_ref
            self._filters = []  # list of (col, op, value)

        def filter(self, clause):
            if isinstance(clause, _Clause):
                self._filters.append((clause.name, clause.op, clause.value))
            return self

        def _matches(self, r: dict) -> bool:
            for col, op, v in self._filters:
                if op == "==":
                    if r.get(col) != v:
                        return False
                elif op == "!=":
                    if r.get(col) == v:
                        return False
                elif op == ">":
                    try:
                        if not (r.get(col, 0) > v):
                            return False
                    except TypeError:
                        return False
            return True

        def all(self):
            return [_AuthSessionRow(**dict(r)) for r in self._rows.values() if self._matches(r)]

        def delete(self, synchronize_session=False):
            kill = [tok for tok, r in self._rows.items() if self._matches(r)]
            for tok in kill:
                del self._rows[tok]
            return len(kill)

        def update(self, values, synchronize_session=False):
            n = 0
            for r in self._rows.values():
                if self._matches(r):
                    for k, new_v in values.items():
                        r[k] = new_v
                    n += 1
            return n

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def query(self, model):
            return _Query(rows)

        def commit(self):
            pass

    class _SessionLocalFactory:
        def __call__(self):
            return _Session()

    import core.database as real_db
    monkeypatch.setattr(real_db, "AuthSession", _AuthSessionCls)
    monkeypatch.setattr(real_db, "SessionLocal", _SessionLocalFactory())

    def _upsert(session, model, conflict_cols, row, update_columns=None):
        tok = row["token"]
        rows[tok] = dict(row)

    def _bulk_upsert(session, model, conflict_cols, rows_list):
        for r in rows_list:
            rows[r["token"]] = dict(r)

    import core.db_upsert as real_dbu
    monkeypatch.setattr(real_dbu, "upsert", _upsert)
    monkeypatch.setattr(real_dbu, "bulk_upsert", _bulk_upsert)

    return rows


def _enable_db_flag(monkeypatch):
    """Flip the infra flag so AuthManager dispatches to the DB path."""
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "sessions_in_db", True)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", True)
    monkeypatch.setitem(feature_flags.features._infra, "sessions_dual_write", False)


def _make_auth_manager(tmp_path: Path):
    """Build a real AuthManager with one user so create_session can succeed."""
    from core.auth import AuthManager
    auth_path = str(tmp_path / "auth.json")
    import json as _json
    import bcrypt as _bcrypt

    _USERS = {
        "alice": {
            "password_hash": _bcrypt.hashpw(b"pw", _bcrypt.gensalt()).decode("utf-8"),
            "is_admin": False,
            "created": time.time(),
        },
        "bob": {
            "password_hash": _bcrypt.hashpw(b"pw", _bcrypt.gensalt()).decode("utf-8"),
            "is_admin": False,
            "created": time.time(),
        },
    }
    with open(auth_path, "w") as f:
        _json.dump({"users": _USERS}, f)
    am = AuthManager(auth_path=auth_path)
    return am


def test_created_session_lands_in_db(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    tok = am.create_session("alice", "pw")
    assert tok is not None
    assert tok in rows
    assert rows[tok]["username"] == "alice"
    assert rows[tok]["expiry"] > time.time()


def test_post_restart_a_live_token_still_validates(monkeypatch, tmp_path):
    """Simulate a process restart by draining the in-memory cache then
    re-loading from DB. ``validate_token`` and
    ``get_username_for_token`` must still succeed."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    tok = am.create_session("alice", "pw")

    # Drain cache + reload from DB.
    with am._sessions_lock:
        am._sessions = {}
    am._load_sessions()

    assert tok in am._sessions
    assert am.validate_token(tok) is True
    assert am.get_username_for_token(tok) == "alice"


def test_post_restart_an_expired_token_is_pruned(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    tok = am.create_session("alice", "pw")
    # Force it to look already-expired then reload.
    rows[tok]["expiry"] = int(time.time()) - 60

    with am._sessions_lock:
        am._sessions = {}
    am._load_sessions()

    assert tok not in am._sessions
    assert am.validate_token(tok) is False


def test_revoke_token_removes_db_row(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    tok = am.create_session("alice", "pw")
    assert tok in rows

    am.revoke_token(tok)
    assert tok not in rows

    # After a restart the token stays gone.
    with am._sessions_lock:
        am._sessions = {}
    am._load_sessions()
    assert tok not in am._sessions


def test_revoke_user_sessions_clears_other_tabs(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    keep = am.create_session("alice", "pw")
    drop = am.create_session("alice", "pw")
    assert keep != drop

    am.revoke_user_sessions("alice", except_token=keep)

    # ``drop`` row gone, ``keep`` row preserved (except_token).
    assert drop not in rows
    assert keep in rows


def test_delete_user_clears_their_db_sessions(monkeypatch, tmp_path):
    """A deleted user must not continue to authenticate. The DB path
    needs the same sweep that the legacy path runs — otherwise a
    restart would resurrect the cookie."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)

    # Promote alice to admin so delete_user can run.
    am._config["users"]["alice"]["is_admin"] = True

    tok = am.create_session("bob", "pw")
    assert rows[tok]["username"] == "bob"

    am.delete_user("bob", requesting_user="alice")

    assert tok not in rows
    with am._sessions_lock:
        am._sessions = {}
    am._load_sessions()
    assert tok not in am._sessions


def test_rename_user_rewrites_db_rows(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_auth_manager(tmp_path)
    am._config["users"]["alice"]["is_admin"] = True

    tok = am.create_session("bob", "pw")
    am.rename_user("bob", "robert", requesting_user="alice")

    # Token survives, owner is rewritten.
    assert tok in rows
    assert rows[tok]["username"] == "robert"


def test_flag_off_keeps_writing_json_blob(monkeypatch, tmp_path):
    """With the flag OFF, AuthManager must keep writing sessions.json —
    existing single-node deployments must be unaffected."""
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "sessions_in_db", False)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", False)

    am = _make_auth_manager(tmp_path)
    sessions_path = am._sessions_path
    tok = am.create_session("alice", "pw")

    import json as _json
    with open(sessions_path, "r") as f:
        blob = _json.load(f)
    assert tok in blob
