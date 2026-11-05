"""Tests for DB-backed memory persistence.

These cover the D.4 dispatch path in ``services.memory.memory.MemoryManager``:

* ``add_entry`` + ``save`` lands a row in the DB keyed by id; ``load``
  reads back from DB by owner.
* A simulated restart (drop in-memory state — for MemoryManager the
  state is purely persistence-backed) returns the same rows.
* ``delete_entry`` and per-owner ``save(..., owner=...)`` reconciliation
  remove rows so they don't resurrect on next load.
* Cross-owner isolation: user A's rows are invisible to user B's
  ``load(owner='B')``.
* Flag-off: behavior is unchanged — legacy JSON file is written.

The real ``core.database.Memory`` SQLAlchemy model iselested by a
dict-backed stub identical in spirit to ``test_auth_session_persistence``.
"""
from __future__ import annotations

import sys
import time
import uuid
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _install_db_stubs(monkeypatch):
    """In-memory row store that mimics the SQLAlchemy query surface used by
    ``MemoryManager`` (``query(Memory).filter(...).all()``, ``.delete()``,
    plus class-attribute comparisons)."""
    rows: dict[str, dict] = {}

    class _Column:
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
        def __init__(self, name, op, value):
            self.name = name
            self.op = op
            self.value = value

        # Negation via ~ — used by the ``~Memory.id.in_(keep)`` filter in
        # ``_db_delete_for_owner_except``. SQLAlchemy clause objects support
        # the bitwise-not operator, so our stub must too.
        def __invert__(self):
            if self.op == "in":
                return _Clause(self.name, "not_in", self.value)
            if self.op == "not_in":
                return _Clause(self.name, "in", self.value)
            if self.op == "==":
                return _Clause(self.name, "!=", self.value)
            if self.op == "!=":
                return _Clause(self.name, "==", self.value)
            raise NotImplementedError(self.op)

    class _InClause(_Clause):
        """Marker subclass so ``filter`` can record an ``in_()`` filter —
        ``_Clause.value`` is the iterable of ids."""

    class _ColumnIn(_Column):
        def in_(self, values):
            return _InClause(self._name, "in", list(values))

    class _MemoryMeta(type):
        def __getattr__(cls, name):
            if name.startswith("__"):
                raise AttributeError(name)
            return _ColumnIn(name)

    class _MemoryRow:
        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _MemoryCls(metaclass=_MemoryMeta):
        __tablename__ = "memories"

        def __init__(self, **kw):
            for k, v in kw.items():
                setattr(self, k, v)

    class _Query:
        def __init__(self):
            self._filters = []

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
                elif op == "in":
                    if r.get(col) not in v:
                        return False
                elif op == "not_in":
                    if r.get(col) in v:
                        return False
                elif op == ">":
                    try:
                        if not (r.get(col, 0) > v):
                            return False
                    except TypeError:
                        return False
            return True

        def all(self):
            return [_MemoryRow(**dict(r)) for r in rows.values() if self._matches(r)]

        def delete(self, synchronize_session=False):
            kill = [k for k, r in rows.items() if self._matches(r)]
            for k in kill:
                del rows[k]
            return len(kill)

    class _Session:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def query(self, model):
            return _Query()

        def commit(self):
            pass

    class _SessionLocalFactory:
        def __call__(self):
            return _Session()

    import core.database as real_db
    monkeypatch.setattr(real_db, "Memory", _MemoryCls)
    monkeypatch.setattr(real_db, "SessionLocal", _SessionLocalFactory())

    def _bulk_upsert(session, model, conflict_cols, rows_list, update_columns=None):
        for r in rows_list:
            rows[r["id"]] = dict(r)

    def _upsert(session, model, conflict_cols, row, update_columns=None):
        rows[row["id"]] = dict(row)

    import core.db_upsert as real_dbu
    monkeypatch.setattr(real_dbu, "bulk_upsert", _bulk_upsert)
    monkeypatch.setattr(real_dbu, "upsert", _upsert)

    return rows


def _enable_db_flag(monkeypatch):
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "memory_in_db", True)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", True)
    monkeypatch.setitem(feature_flags.features._infra, "memory_dual_write", False)


def _make_manager(tmp_path: Path):
    from services.memory.memory import MemoryManager
    return MemoryManager(str(tmp_path))


def test_add_and_load_round_trips_db(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    e = am.add_entry("alice likes coffee", source="auto", category="preference", owner="alice")
    am.save([e])

    assert e["id"] in rows
    assert rows[e["id"]]["owner"] == "alice"
    assert rows[e["id"]]["text"] == "alice likes coffee"

    loaded = am.load(owner="alice")
    assert len(loaded) == 1
    assert loaded[0]["text"] == "alice likes coffee"


def test_load_filtered_by_owner(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    a1 = am.add_entry("alice fact 1", owner="alice")
    a2 = am.add_entry("alice fact 2", owner="alice")
    b1 = am.add_entry("bob fact 1", owner="bob")
    am.save([a1, a2, b1])

    # load(owner=) must go through the DB filter, not the client.
    alice_loaded = am.load(owner="alice")
    assert {m["id"] for m in alice_loaded} == {a1["id"], a2["id"]}

    bob_loaded = am.load(owner="bob")
    assert {m["id"] for m in bob_loaded} == {b1["id"]}


def test_post_restart_load_is_stable(monkeypatch, tmp_path):
    """Simulate a restart: under DB-only there is no in-memory cache, so a
    fresh ``load(owner=)`` call after the writer is gone still returns the
    rows written prior."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    e = am.add_entry("persistent fact", owner="alice")
    am.save([e])

    # New process: new MemoryManager instance pointing at the same DB.
    am2 = _make_manager(tmp_path)
    loaded = am2.load(owner="alice")
    assert len(loaded) == 1
    assert loaded[0]["id"] == e["id"]


def test_delete_entry_removes_row(monkeypatch, tmp_path):
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    e = am.add_entry("ephemeral fact", owner="alice")
    am.save([e])
    assert e["id"] in rows

    ok = am.delete_entry(e["id"])
    assert ok is True
    assert e["id"] not in rows

    # After a restart the row stays gone.
    am2 = _make_manager(tmp_path)
    assert am2.load(owner="alice") == []


def test_save_with_owner_reconciles_deletions(monkeypatch, tmp_path):
    """A route that loads → mutates → ``save(entries, owner='alice')``
    must drop DB rows for alice whose id is no longer in ``entries``.
    Without this, ``delete_memory`` would have its effect reversed by a
    subsequent load."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    e1 = am.add_entry("keep", owner="alice")
    e2 = am.add_entry("drop", owner="alice")
    am.save([e1, e2])

    # Simulate delete: list minus e2, save with owner scope.
    am.save([e1], owner="alice")

    assert e1["id"] in rows
    assert e2["id"] not in rows


def test_save_with_owner_does_not_touch_other_users(monkeypatch, tmp_path):
    """``save(..., owner='alice')`` must not delete bob's rows when
    alice's list happens not to contain them. This is the core
    multi-tenant guarantee the per-owner scope buys us."""
    rows = _install_db_stubs(monkeypatch)
    _enable_db_flag(monkeypatch)
    am = _make_manager(tmp_path)

    a = am.add_entry("alice fact", owner="alice")
    b = am.add_entry("bob fact", owner="bob")
    am.save([a, b])

    am.save([a], owner="alice")
    assert b["id"] in rows


def test_flag_off_writes_json_only(monkeypatch, tmp_path):
    """With the flag OFF, MemoryManager must keep writing memory.json —
    existing single-node deployments must be unaffected."""
    from core import feature_flags
    monkeypatch.setitem(feature_flags.features._infra, "memory_in_db", False)
    monkeypatch.setitem(feature_flags.features._infra, "multitenant_postgres", False)

    am = _make_manager(tmp_path)
    e = am.add_entry("legacy fact", owner="alice")
    am.save([e])

    import json as _json
    memory_path = am.memory_file
    with open(memory_path, "r", encoding="utf-8") as f:
        blob = _json.load(f)
    ids = [entry["id"] for entry in blob]
    assert e["id"] in ids
