"""Round-trip tests for the owner-scoped ``services.research.research_store``.

These cover the four scenarios the migration plan calls out:

* Owner A's research is retrievable by owner A and invisible to owner B
  under the MinIO path (no cross-tenant leak by id).
* Round-trip under per-user + admin owner names.
* Dual-write splits the row across both stores during cutover.
* MinIO-unhealthy writes fall through to the on-disk FS fallback so a
  store outage never makes research data unreachable.

Plus two integrity checks:

* Path-traversal ids (``../etc/passwd``) are rejected before touching
  the object key or filesystem.
* Flag-off path persists to the legacy flat directory so existing
  deployments behave unchanged.
"""
from __future__ import annotations

import json
import sys
import types
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _import_research_store():
    import importlib
    from services.research import research_store
    return importlib.reload(research_store)


def _make_object_store_stub(should_fail_write: bool = False):
    """In-memory fake of ``src.object_store.store`` keyed by
    ``(user_id, key)``. Yields ``userdata/{owner}/...`` full keys so the
    list enumerate path slices them back to rids correctly."""
    blobs: dict[tuple[str, str], bytes] = {}

    class _FakeStore:
        enabled = True
        healthy = True

        def put_user_object(self, user_id, key, data, content_type="application/octet-stream"):
            if should_fail_write:
                raise RuntimeError("simulated MinIO outage")
            blobs[(user_id, key)] = bytes(data)

        def get_user_object(self, user_id, key):
            return blobs.get((user_id, key))

        def delete_user_object(self, user_id, key):
            if (user_id, key) in blobs:
                del blobs[(user_id, key)]
                return True
            return False

        def list_user_objects(self, user_id, prefix="", recursive=True):
            for (uid, short_key) in list(blobs.keys()):
                full_key = f"userdata/{uid}/{short_key}"
                if uid == user_id and full_key.startswith(f"userdata/{user_id}/{prefix}"):
                    yield full_key

    fake_store = _FakeStore()
    fake_module = types.ModuleType("src.object_store")
    fake_module.store = fake_store
    return fake_module, fake_store, blobs


def _install_stubs(monkeypatch, should_fail_write: bool = False):
    os_module, fake_store, blobs = _make_object_store_stub(should_fail_write)
    monkeypatch.setitem(sys.modules, "src.object_store", os_module)
    return fake_store, blobs


def _enable_flag(monkeypatch, **flags):
    from core import feature_flags
    for k, v in flags.items():
        monkeypatch.setitem(feature_flags.features._infra, k, v)


def test_round_trip_owner_scoped(monkeypatch):
    """Save under owner_a; load by owner_a returns data; load by owner_b
    returns None (no cross-tenant leak by id)."""
    _install_stubs(monkeypatch)
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    rs = _import_research_store()

    payload = {"query": "q", "summary": "s", "owner": "owner_a"}
    rs.save("owner_a", "rid-aaa", payload)

    loaded = rs.load("owner_a", "rid-aaa")
    assert loaded is not None
    assert loaded["query"] == "q"

    assert rs.load("owner_b", "rid-aaa") is None


def test_admin_and_per_user_round_trip(monkeypatch):
    """Admin and per-user rows both survive a save/load cycle and do not
    collide."""
    _install_stubs(monkeypatch)
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    rs = _import_research_store()

    rs.save("admin@example", "rid-admin", {"summary": "admin-row"})
    rs.save("alice@example", "rid-alice", {"summary": "alice-row"})

    assert rs.load("admin@example", "rid-admin")["summary"] == "admin-row"
    assert rs.load("alice@example", "rid-alice")["summary"] == "alice-row"
    # No collision: each owner has only their own row.
    assert rs.load("admin@example", "rid-alice") is None
    assert rs.load("alice@example", "rid-admin") is None


def test_owner_cannot_delete_foreign_row(monkeypatch):
    """Delete is owner-scoped: B's delete on A's row does nothing; A's
    row still loads afterwards."""
    fake_store, blobs, *_ = (), (), None
    fake_store, blobs = _install_stubs(monkeypatch)[:2]
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    rs = _import_research_store()

    rs.save("owner_a", "rid-shared", {"summary": "a"})
    deleted = rs.delete("owner_b", "rid-shared")
    assert deleted is False
    # A's row still loadable.
    assert rs.load("owner_a", "rid-shared") is not None
    # And there is no object key under owner_b.
    assert all(uid != "owner_b" for (uid, _k) in blobs)


def test_list_ids_owner_scoped(monkeypatch):
    _install_stubs(monkeypatch)
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    rs = _import_research_store()

    rs.save("owner_a", "rid-a1", {"owner": "owner_a"})
    rs.save("owner_a", "rid-a2", {"owner": "owner_a"})
    rs.save("owner_b", "rid-b1", {"owner": "owner_b"})

    assert sorted(rs.list_ids("owner_a")) == ["rid-a1", "rid-a2"]
    assert sorted(rs.list_ids("owner_b")) == ["rid-b1"]


def test_dual_write_writes_both_stores(monkeypatch, tmp_path):
    """Under dual-write, the per-owner object is written AND the legacy
    flat file is updated — so the cutover is reversible."""
    _, blobs = _install_stubs(monkeypatch)[:2]
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=True,
    )
    # The legacy flat path is created relative to CWD; isolate it.
    monkeypatch.chdir(tmp_path)
    rs = _import_research_store()

    rs.save("owner_a", "rid-dw", {"summary": "both"})

    # MinIO object written.
    assert ("owner_a", "research/rid-dw.json") in blobs
    # Legacy flat file written.
    legacy = tmp_path / "data" / "deep_research" / "rid-dw.json"
    assert legacy.exists()
    assert json.loads(legacy.read_text())["summary"] == "both"


def test_minio_unhealthy_falls_back_to_fs(monkeypatch, tmp_path):
    """When MinIO write raises, research_store falls through to the
    on-disk fallback under ``data/userdata/{owner}/research/<id>.json``."""
    # Build a store that fails writes but is marked healthy (the dual
    # code-path: store is up, mid-call write fails).
    os_module, fake_store, blobs = _make_object_store_stub(should_fail_write=True)
    monkeypatch.setitem(sys.modules, "src.object_store", os_module)

    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    monkeypatch.chdir(tmp_path)
    rs = _import_research_store()

    rs.save("owner_a", "rid-fb", {"summary": "fallback row"})

    # No MinIO object made it.
    assert blobs == {}
    # Fallback file exists.
    fb = tmp_path / "data" / "userdata" / "owner_a" / "research" / "rid-fb.json"
    assert fb.exists()
    assert json.loads(fb.read_text())["summary"] == "fallback row"

    # And load can read it back even though MinIO is empty.
    loaded = rs.load("owner_a", "rid-fb")
    assert loaded is not None
    assert loaded["summary"] == "fallback row"


def test_invalid_rid_rejected(monkeypatch):
    """Path-traversal ids never reach the object key or filesystem."""
    _install_stubs(monkeypatch)
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=False,
    )
    rs = _import_research_store()

    for bad in ("../etc/passwd", "", "rid with spaces", "rid/with/slashes", "rid|pipes"):
        with pytest.raises(ValueError):
            rs.save("owner_a", bad, {"x": 1})
        with pytest.raises(ValueError):
            rs.load("owner_a", bad)
        with pytest.raises(ValueError):
            rs.delete("owner_a", bad)


def test_legacy_path_when_flag_off(monkeypatch, tmp_path):
    """Flag off: writes/reads hit the legacy ``data/deep_research/``
    flat directory with an owner field check (existing deployments
    behave unchanged)."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, research_in_minio=False)
    monkeypatch.chdir(tmp_path)
    rs = _import_research_store()

    rs.save("owner_a", "rid-legacy", {"summary": "l", "owner": "owner_a"})

    # Owner scoped.
    assert rs.load("owner_a", "rid-legacy")["summary"] == "l"
    assert rs.load("owner_b", "rid-legacy") is None

    # File lives at the old flat path.
    flat = tmp_path / "data" / "deep_research" / "rid-legacy.json"
    assert flat.exists()


def test_owner_filter_in_list_under_dual_write(monkeypatch, tmp_path):
    """Under dual-write, owner B's list_ids should not see owner A's
    legacy flat file even though it exists."""
    _install_stubs(monkeypatch)
    _enable_flag(
        monkeypatch,
        research_in_minio=True,
        research_dual_write=True,
    )
    monkeypatch.chdir(tmp_path)
    rs = _import_research_store()

    rs.save("owner_a", "rid-dw-list", {"owner": "owner_a", "summary": "a"})

    # Sanity: A sees it.
    assert "rid-dw-list" in list(rs.list_ids("owner_a"))
    # B does not see A's row (owner field on the legacy file protects it).
    assert "rid-dw-list" not in list(rs.list_ids("owner_b"))
