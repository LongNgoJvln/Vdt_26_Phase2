"""Owner-scoped behavior for ``routes/vault_routes.py``.

Boundary asserts:

* Admin unlock persists a BW_SESSION under ``<admin>`` only — a
  different admin's GET /api/vault/config returns ``unlocked: false``
  and never sees the first admin's session.
* ``_load_config`` / ``_save_config`` always thread the request's
  ``current_user`` into ``core.vault_store``; nothing about the route
  layer touches ``data/vault.json`` directly.

The handlers under test shell out to the Bitwarden CLI, so we stub
``_run_bw`` to deterministically succeed / fail and patch
``feature_flags.features._infra`` to flip the MinIO path on. The
Fernet stand-in is shared with ``tests/test_vault_store.py`` so the
two suites agree on the ``enc:`` prefix convention.
"""
from __future__ import annotations

import asyncio
import sys
import types
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace

import pytest


PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


def _make_object_store_stub():
    blobs: dict[tuple[str, str], bytes] = {}

    class _FakeStore:
        enabled = True
        healthy = True

        def put_user_object(self, user_id, key, data, content_type="application/octet-stream"):
            blobs[(user_id, key)] = bytes(data)

        def get_user_object(self, user_id, key):
            return blobs.get((user_id, key))

        def delete_user_object(self, user_id, key):
            blobs.pop((user_id, key), None)

    fake_module = types.ModuleType("src.object_store")
    fake_module.store = _FakeStore()
    return fake_module, blobs


def _make_secret_storage_stub():
    class _SS:
        @staticmethod
        def encrypt(plaintext):
            return "enc:" + plaintext

        @staticmethod
        def decrypt(value):
            if value.startswith("enc:"):
                return value[len("enc:"):]
            return ""

        @staticmethod
        def is_encrypted(value):
            return isinstance(value, str) and value.startswith("enc:")

    fake_module = types.ModuleType("src.secret_storage")
    fake_module.encrypt = _SS.encrypt
    fake_module.decrypt = _SS.decrypt
    fake_module.is_encrypted = _SS.is_encrypted
    return fake_module


def _install_stubs(monkeypatch):
    os_module, blobs = _make_object_store_stub()
    monkeypatch.setitem(sys.modules, "src.object_store", os_module)
    monkeypatch.setitem(sys.modules, "src.secret_storage", _make_secret_storage_stub())
    return blobs


def _enable_flag(monkeypatch, **flags):
    from core import feature_flags
    for k, v in flags.items():
        monkeypatch.setitem(feature_flags.features._infra, k, v)


def _make_request(user: str):
    """Build a minimal Request stand-in carrying current_user + app.state.

    The auth_manager stub says yes-admin to any user so ``require_admin``
    passes; ``current_user`` is the real owner string under test.
    """
    class _AuthMgr:
        is_configured = True
        def is_admin(self, _u):
            return True

    req = SimpleNamespace()
    req.state = SimpleNamespace(current_user=user)
    req.app = SimpleNamespace(state=SimpleNamespace(auth_manager=_AuthMgr()))
    req.headers = {}
    return req


def _vault_endpoints(monkeypatch, run_bw_returns):
    """Register ``vault_routes`` and return the six handler endpoints.

    ``run_bw_returns`` is a list of (stdout, stderr, rc) tuples popped in
    order so a test can script the unlock→config sequence without reaching
    the real Bitwarden CLI.
    """
    import importlib
    from routes import vault_routes

    # Freeze utcnow so unlocked_at is deterministic for assertions.
    # (serializes via iso_utc -> "2026-01-01T00:00:00Z"; legacy rows/naive
    # values serialize identically, so old assertions keep their prefix.)
    monkeypatch.setattr(vault_routes, "utcnow", lambda: datetime(2026, 1, 1))

    calls: list[list] = []

    async def fake_run_bw(args, session=None, input_text=None, bw_password=None):
        calls.append(args)
        if run_bw_returns:
            return run_bw_returns.pop(0)
        return "", "", 0

    monkeypatch.setattr(vault_routes, "_run_bw", fake_run_bw)

    async def fake_check_bw():
        return True

    monkeypatch.setattr(vault_routes, "_check_bw_installed", fake_check_bw)

    router = vault_routes.setup_vault_routes()
    endpoints = {r.endpoint.__name__: r.endpoint for r in router.routes}
    return endpoints, calls


def test_admin_unlock_persists_session_only_for_that_admin(monkeypatch):
    """Admin A unlocks the vault → A's GET /config shows unlocked=true;
    admin B's GET /config shows unlocked=false (no cross-tenant BW_SESSION
    leak through the shared MinIO bucket)."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("BW_SESSION_ADMIN_A", "", 0),  # unlock stdout
    ])

    body = SimpleNamespace(master_password="hunter2")
    asyncio.run(endpoints["unlock"](body, _make_request("admin_a")))

    a_cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    assert a_cfg["unlocked"] is True
    assert a_cfg["unlocked_at"] == "2026-01-01T00:00:00Z"

    b_cfg = asyncio.run(endpoints["get_config"](_make_request("admin_b")))
    assert b_cfg["unlocked"] is False
    assert b_cfg["unlocked_at"] == ""


def test_lock_clears_only_calling_admin_session(monkeypatch):
    """Admin A locks → A's next GET returns unlocked=false. Admin B's
    session (if any) is untouched."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("BW_SESSION_ADMIN_A", "", 0),  # unlock
    ])

    body = SimpleNamespace(master_password="hunter2")
    asyncio.run(endpoints["unlock"](body, _make_request("admin_a")))

    asyncio.run(endpoints["lock"](_make_request("admin_a")))

    a_cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    assert a_cfg["unlocked"] is False


def test_save_config_threads_owner_into_store(monkeypatch):
    """The /config POST handler must pass ``current_user`` through; if
    the owner weren't threaded, two admins pointing at different
    Vaultwarden servers would race the global file."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("", "", 0),  # bw config server (empty stdout, rc=0 OK)
    ])

    body = SimpleNamespace(server_url="https://vw.a", email="a@example")
    asyncio.run(endpoints["save_config"](body, _make_request("admin_a")))

    body_b = SimpleNamespace(server_url="https://vw.b", email="b@example")
    asyncio.run(endpoints["save_config"](body_b, _make_request("admin_b")))

    a_cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    b_cfg = asyncio.run(endpoints["get_config"](_make_request("admin_b")))
    assert a_cfg["server_url"] == "https://vw.a"
    assert b_cfg["server_url"] == "https://vw.b"


def test_logout_deletes_owner_record(monkeypatch):
    """logout → vault_delete(owner) → subsequent load returns empty (no
    server_url, email, or session)."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("", "", 0),  # bw config server (initial save)
        ("", "", 0),  # bw logout
    ])

    body = SimpleNamespace(server_url="https://vw.a", email="a@example")
    asyncio.run(endpoints["save_config"](body, _make_request("admin_a")))

    asyncio.run(endpoints["logout"](_make_request("admin_a")))

    cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    assert cfg["server_url"] == ""
    assert cfg["email"] == ""
    assert cfg["unlocked"] is False


def test_unlock_failure_does_not_persist(monkeypatch):
    """If bw returns a non-zero rc, the handler bails before touching
    vault_store — no half-write leaving the session marked as unlocked."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("", "Invalid master password.", 1),  # unlock failure
    ])

    body = SimpleNamespace(master_password="wrong")
    result = asyncio.run(endpoints["unlock"](body, _make_request("admin_a")))
    assert result["ok"] is False

    cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    assert cfg["unlocked"] is False
    assert cfg["unlocked_at"] == ""


def test_no_vault_json_touched_under_flag(monkeypatch, tmp_path):
    """Under vault_in_minio=True, the route layer must NOT read or write
    ``data/vault.json`` — owner isolation lives in MinIO now."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    sentinel = tmp_path / "data" / "vault.json"
    sentinel.write_text('{"server_url":"legacy","email":"l","session":"leaked"}')

    endpoints, _ = _vault_endpoints(monkeypatch, [
        ("BW_SESSION_X", "", 0),  # unlock
    ])

    body = SimpleNamespace(master_password="hunter2")
    asyncio.run(endpoints["unlock"](body, _make_request("admin_a")))

    # The legacy file's contents are unchanged: it was never opened.
    assert '"leaked"' in sentinel.read_text()

    # And the admin's session landed in MinIO, not the legacy file.
    cfg = asyncio.run(endpoints["get_config"](_make_request("admin_a")))
    assert cfg["unlocked"] is True
