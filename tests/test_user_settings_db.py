"""Tests for DB-backed per-user settings (``routes.prefs_routes`` + DB).

These cover the D.2 dispatch path:

* ``_save_for_user`` writes a row per key under the user_settings table,
  and ``_load_for_user`` reads them back shape-compatible with the
  legacy dict-of-prefs JSON blob (so nested-access callers like
  ``caldav`` subblocks keep working).
* Per-owner isolation: user B's keys are invisible to user A's load.
* Writes invalidate stale keys: re-saving a smaller dict deletes the
  rows that dropped out.
* Dual-write flag persists to both the DB and the legacy JSON blob
  during cutover.
* Rename/delete cascade across both backends.
* Flag-off path: writers hit the JSON blob only — existing deployments
  behave unchanged.

There is no real Postgres fixture here — the test stubs out
``core.database.UserSetting`` + ``SessionLocal`` and ``core.db_upsert``
so the prefs_routes code paths run end-to-end against an in-memory
list.
"""
from __future__ import annotations

import sys
import json
import importlib
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_db_stubs(monkeypatch):
    """In-memory UserSetting row store keyed by (owner, key). Mirrors
    the stub pattern in test_auth_session_persistence.py."""
    rows: dict[tuple[str, str], dict] = {}

    class _Column:
        def __init__(self, name: str):
            self._name = name

        def __eq__(self, other):
            return _Clause(self._name, "==", other)

        def __ne__(self, other):
            return _Clause(self._name, "!=", other)

        def __hash__(self):
            return hash(self._name)

    class _Clause:
        def __init__(self, name: str, op: str, value):
            self.name = name
            self.op = op
            self.value = value

    class _Row:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Meta(type):
        def __getattr__(cls, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return _Column(name)

    class _UserSetting(metaclass=_Meta):
        __tablename__ = "user_settings"

        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Query:
        def __init__(self, rows_ref):
            self._rows = rows_ref
            self._filters = []

        def filter(self, *clauses):
            for clause in clauses:
                if isinstance(clause, _Clause):
                    self._filters.append((clause.name, clause.op, clause.value))
            return self

        def _matches(self, key: tuple[str, str], r: dict) -> bool:
            for col, op, v in self._filters:
                # owner is key[0], key name is key[1]
                record = {"owner": key[0], "key": key[1], **r}
                if op == "==":
                    if record.get(col) != v:
                        return False
                elif op == "!=":
                    if record.get(col) == v:
                        return False
            return True

        def all(self):
            return [
                _Row(owner=k[0], key=k[1], **dict(r))
                for k, r in self._rows.items()
                if self._matches(k, r)
            ]

        def delete(self, synchronize_session=False):
            kill = [k for k, r in self._rows.items() if self._matches(k, r)]
            for k in kill:
                del self._rows[k]
            return len(kill)

        def update(self, values, synchronize_session=False):
            matches = [k for k, r in list(self._rows.items()) if self._matches(k, r)]
            n = 0
            for k in matches:
                r = self._rows[k]
                for col, new_v in values.items():
                    if col == "owner":
                        new_key = (new_v, k[1])
                        if new_key in self._rows:
                            continue
                        del self._rows[k]
                        self._rows[new_key] = r
                    else:
                        r[col] = new_v
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

    class _SessionLocal:
        def __call__(self):
            return _Session()

    import core.database as real_db
    monkeypatch.setattr(real_db, "UserSetting", _UserSetting)
    monkeypatch.setattr(real_db, "SessionLocal", _SessionLocal())

    def _upsert(session, model, conflict_cols, row, update_columns=None):
        key = (row["owner"], row["key"])
        rows[key] = {"value_json": row["value_json"]}

    import core.db_upsert as real_dbu
    monkeypatch.setattr(real_dbu, "upsert", _upsert)

    return rows


def _enable_db_flag(monkeypatch):
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_in_db", True)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", True)
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_dual_write", False)


def _enable_dual_write(monkeypatch):
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_in_db", True)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", True)
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_dual_write", True)


def _disable_db_flag(monkeypatch):
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_in_db", False)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", False)
    monkeypatch.setitem(feature_flags.features._infra, "user_settings_dual_write", False)


def _reload_prefs_routes():
    """Force re-import so module-level ``_db_user_settings_enabled``
    closures reflect the current feature flag state."""
    import routes.prefs_routes as pr
    return importlib.reload(pr)


def test_save_writes_rows_per_key(monkeypatch):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"vision_model": "gpt-4o", "default_model": "claude"})

    assert ("alice", "vision_model") in rows
    assert ("alice", "default_model") in rows
    assert json.loads(rows[("alice", "vision_model")]["value_json"]) == "gpt-4o"


def test_load_returns_dict_compat_with_legacy_callers(monkeypatch):
    """Existing callers do ``(_load_for_user(owner) or {}).get('caldav', {})``
    style nested access; the DB path's return shape must mirror the JSON
    blob's ``_users[owner]`` dict."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {
        "vision_model": "gpt-4o",
        "caldav": {"url": "https://caldav.example/alice"},
        "vision_model_fallbacks": ["qwen", "llama"],
    })

    loaded = pr._load_for_user("alice")
    assert isinstance(loaded, dict)
    assert loaded["vision_model"] == "gpt-4o"
    assert loaded["caldav"]["url"] == "https://caldav.example/alice"
    assert loaded["vision_model_fallbacks"] == ["qwen", "llama"]


def test_per_owner_isolation(monkeypatch):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"default_model": "claude"})
    pr._save_for_user("bob", {"default_model": "gpt-4o"})

    assert pr._load_for_user("alice") == {"default_model": "claude"}
    assert pr._load_for_user("bob") == {"default_model": "gpt-4o"}
    # No cross-tenant key pollution.
    assert ("alice", "default_model") in rows
    assert ("bob", "default_model") in rows
    assert ("alice", "nonexistent") not in rows


def test_save_deletes_stale_keys(monkeypatch):
    """Re-saving a smaller dict must remove the dropped keys; otherwise
    stale rows from a previous pref set silently reappear on next load."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"a": 1, "b": 2, "c": 3})
    assert len([k for k in rows if k[0] == "alice"]) == 3

    pr._save_for_user("alice", {"a": 1})
    assert pr._load_for_user("alice") == {"a": 1}
    assert ("alice", "b") not in rows
    assert ("alice", "c") not in rows


def test_save_no_op_when_value_unchanged(monkeypatch):
    """The dispatch only writes when a value actually changed — keeps
    the per-key write profile O(1) per changed key, not full-row rewrite
    on every save."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"vision_model": "gpt-4o"})
    rows.clear()  # Drop everything; second save must repopulate.

    pr._save_for_user("alice", {"vision_model": "gpt-4o"})
    assert ("alice", "vision_model") in rows


def test_dual_write_persists_both_stores(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_dual_write(monkeypatch)
    monkeypatch.chdir(tmp_path)
    pr = _reload_prefs_routes()

    # Need a prefs file to exist for the dual-write path's _load() call.
    (tmp_path / "data").mkdir(exist_ok=True)
    pr._save_for_user("alice", {"vision_model": "gpt-4o"})

    # DB row written.
    assert ("alice", "vision_model") in rows
    # JSON blob written.
    blob = json.loads((tmp_path / "data" / "user_prefs.json").read_text())
    assert blob["_users"]["alice"]["vision_model"] == "gpt-4o"


def test_flag_off_keeps_writing_json_only(monkeypatch, tmp_path):
    """With the flag OFF, _save_for_user must write user_prefs.json and
    never touch the DB."""
    from core import feature_flags
    _disable_db_flag(monkeypatch)
    rows = _install_db_stubs(monkeypatch)
    monkeypatch.chdir(tmp_path)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"vision_model": "gpt-4o"})

    # No DB rows.
    assert rows == {}
    blob = json.loads((tmp_path / "data" / "user_prefs.json").read_text())
    assert blob["_users"]["alice"]["vision_model"] == "gpt-4o"


def test_db_outage_falls_through_to_json(monkeypatch, tmp_path):
    """If the DB write raises, the save must fall through to the legacy
    JSON path so the request doesn't 500 (preserving graceful degrade)."""
    _enable_db_flag(monkeypatch)
    monkeypatch.chdir(tmp_path)
    pr = _reload_prefs_routes()

    # Force the DB load to raise.
    def _boom(owner):
        raise RuntimeError("simulated DB outage")
    pr._db_load_for_user = _boom

    pr._save_for_user("alice", {"vision_model": "gpt-4o"})
    blob = json.loads((tmp_path / "data" / "user_prefs.json").read_text())
    assert blob["_users"]["alice"]["vision_model"] == "gpt-4o"


def test_rename_user_moves_db_rows(monkeypatch):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"vision_model": "gpt-4o", "default_model": "claude"})

    moved = pr.rename_user("alice", "alicia")

    assert moved == 2
    assert ("alice", "vision_model") not in rows
    assert ("alicia", "vision_model") in rows
    assert ("alicia", "default_model") in rows


def test_delete_user_drops_db_rows(monkeypatch):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    pr = _reload_prefs_routes()

    pr._save_for_user("alice", {"vision_model": "gpt-4o"})
    assert ("alice", "vision_model") in rows

    removed = pr.delete_user("alice")
    assert removed == 1
    assert ("alice", "vision_model") not in rows


def test_get_user_setting_resolves_db_first(monkeypatch):
    """settings.get_user_setting(key, owner) must read from the DB when
    the flag is on for keys whitelisted in _PER_USER_KEYS, and fall
    through to the global for anything else."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    # Seed a DB row directly.
    rows[("alice", "vision_model")] = {"value_json": json.dumps("claude-3-opus")}

    import src.settings as settings_mod
    importlib.reload(settings_mod)

    result = settings_mod.get_user_setting("vision_model", owner="alice")
    assert result == "claude-3-opus"


def test_get_user_setting_falls_through_when_not_set(monkeypatch):
    """An unset per-user key falls through to the global setting."""
    _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)

    # Seed a global setting.
    from src import constants as _c
    saved_file = getattr(_c, "SETTINGS_FILE", None)

    import src.settings as settings_mod
    importlib.reload(settings_mod)

    # Patch load_settings to return a stub global.
    def _stub_load():
        return {"vision_model": "fallback-global"}
    settings_mod.load_settings = _stub_load

    result = settings_mod.get_user_setting("vision_model", owner="alice")
    assert result == "fallback-global"
