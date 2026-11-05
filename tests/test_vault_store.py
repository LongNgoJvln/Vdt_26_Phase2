"""Round-trip tests for the owner-scoped ``core.vault_store``.

These cover:

* Owner A's saved config is retrievable by owner A and invisible to
  owner B (returns ``{}``) under the MinIO path.
* Legacy path (flag off) keeps writing / reading ``data/vault.json`` so
  existing deployments behave unchanged.
* The persisted object in MinIO carries the Fernet prefix — secrets
  never land in plaintext.
* Only whitelisted keys survive a round-trip — future callers can't
  smuggle in stray fields.
* ``save`` raises ``RuntimeError`` when MinIO is unreachable so an
  unlock failure is never silently swallowed.
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


def _import_vault_store():
    # Re-import after each monkeypatch cycle so the module picks up the
    # current src.object_store / src.secret_storage dummies.
    import importlib
    import core.vault_store as vs
    importlib.reload(vs)
    return vs


def _make_object_store_stub(should_fail_write: bool = False):
    """Build a fake ``src.object_store.store`` singleton plus the module
    surface used by ``vault_store``."""
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
            blobs.pop((user_id, key), None)

    fake_store = _FakeStore()
    fake_module = types.ModuleType("src.object_store")
    fake_module.store = fake_store
    return fake_module, fake_store, blobs


def _make_secret_storage_stub():
    """Minimal Fernet stand-in: prefix ciphertext with ``enc:`` so the
    vault_is_encrypted_at_rest test can assert the marker."""
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


def _install_stubs(monkeypatch, should_fail_write: bool = False):
    os_module, fake_store, blobs = _make_object_store_stub(should_fail_write)
    ss_module = _make_secret_storage_stub()
    monkeypatch.setitem(sys.modules, "src.object_store", os_module)
    monkeypatch.setitem(sys.modules, "src.secret_storage", ss_module)
    return fake_store, blobs, ss_module


def _enable_flag(monkeypatch, **flags):
    """Patch the live feature_flags singleton's _infra dict so the
    in-process ``infra_enabled()`` check picks up overrides."""
    from core import feature_flags
    for k, v in flags.items():
        monkeypatch.setitem(feature_flags.features._infra, k, v)


def test_round_trip_owner_scoped(monkeypatch):
    """Save under owner_a, load by owner_a returns the config; load by
    owner_b returns ``{}`` (no cross-tenant leak)."""
    fake_store, blobs, _ = _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)

    vs = _import_vault_store()

    cfg_a = {"server_url": "https://vw.example", "email": "a@example",
             "session": "BW_SESSION_A", "unlocked_at": "2026-08-18T12:00:00"}
    vs.save("owner_a", cfg_a)

    loaded = vs.load("owner_a")
    assert loaded["session"] == "BW_SESSION_A"
    assert loaded["email"] == "a@example"

    # owner_b sees nothing
    assert vs.load("owner_b") == {}

    # And the MinIO object key was namespaced under owner_a
    assert ("owner_a", "vault.json.enc") in blobs
    assert ("owner_b", "vault.json.enc") not in blobs


def test_persisted_object_is_encrypted(monkeypatch):
    """The bytes written to MinIO carry the Fernet prefix — the
    ``src.secret_storage.encrypt`` indirection is mandatory, never a
    raw ``json.dumps`` to the bucket. (A real Fernet cipher would also
    hide the plaintext; here we only verify the prefix because the
    stub's "cipher" just prepends ``enc:``.)"""
    _, blobs, ss = _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)
    vs = _import_vault_store()

    vs.save("owner_a", {"server_url": "x", "email": "a", "session": "secret"})

    blob = blobs[("owner_a", "vault.json.enc")].decode("utf-8")
    assert ss.is_encrypted(blob), f"vault payload not encrypted: {blob!r}"


def test_only_whitelisted_keys_persist(monkeypatch):
    """The store drops anything outside the _ALLOWED_KEYS whitelist so
    callers can't smuggle in stray fields at the boundary."""
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)
    vs = _import_vault_store()

    vs.save("owner_a", {
        "server_url": "https://vw",
        "email": "a",
        "session": "s",
        "unlocked_at": "now",
        "evil_extra": "should be dropped",
    })
    loaded = vs.load("owner_a")
    assert "evil_extra" not in loaded
    assert set(loaded.keys()) == {"server_url", "email", "session", "unlocked_at"}


def test_save_failure_raises(monkeypatch):
    """A MinIO write outage must surface — secrets NEVER get silently
    dropped to in-memory-only state."""
    _install_stubs(monkeypatch, should_fail_write=True)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)
    vs = _import_vault_store()

    with pytest.raises(RuntimeError):
        vs.save("owner_a", {"server_url": "x", "email": "a", "session": "s"})


def test_load_failure_returns_empty(monkeypatch):
    """A MinIO read outage surfaces as ``{}`` — never 500 on secret reads."""
    os_module, _, _ = _make_object_store_stub()
    # Make get_user_object throw instead of return None
    class _SickStore:
        enabled = True
        healthy = True
        def put_user_object(self, *a, **kw): raise RuntimeError("nope")
        def get_user_object(self, *a, **kw): raise RuntimeError("read outage")
        def delete_user_object(self, *a, **kw): raise RuntimeError("del outage")
    os_module.store = _SickStore()
    monkeypatch.setitem(sys.modules, "src.object_store", os_module)
    monkeypatch.setitem(sys.modules, "src.secret_storage", _make_secret_storage_stub())
    _enable_flag(monkeypatch, vault_in_minio=True)
    vs = _import_vault_store()
    # Should return {} rather than raise
    assert vs.load("owner_a") == {}


def test_clear_session_strips_session_field(monkeypatch):
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)
    vs = _import_vault_store()

    vs.save("owner_a", {"server_url": "x", "email": "a", "session": "s",
                        "unlocked_at": "now"})
    vs.clear_session("owner_a")
    loaded = vs.load("owner_a")
    assert "session" not in loaded
    assert "unlocked_at" not in loaded
    # Non-session fields survive.
    assert loaded["email"] == "a"


def test_delete_removes_record(monkeypatch):
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=True, vault_dual_write=False)
    vs = _import_vault_store()
    vs.save("owner_a", {"server_url": "x", "email": "a", "session": "s"})
    vs.delete("owner_a")
    assert vs.load("owner_a") == {}


def test_legacy_path_when_flag_off(monkeypatch, tmp_path):
    """When the flag is off, the store falls back to the legacy global
    data/vault.json — existing deployments are unaffected."""
    # Even with MinIO stubs in place, the dispatch should ignore them.
    _install_stubs(monkeypatch)
    _enable_flag(monkeypatch, vault_in_minio=False)

    # The legacy path uses Path("data/vault.json") relative to CWD.
    # Point it at tmp_path so the test doesn't touch real state.
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data").mkdir()
    legacy = tmp_path / "data" / "vault.json"
    legacy.write_text(json.dumps({"server_url": "https://legacy",
                                  "email": "l@example",
                                  "session": "legacy-session-key"}))

    vs = _import_vault_store()
    loaded = vs.load("anybody")  # owner ignored on legacy path
    assert loaded["session"] == "legacy-session-key"
    assert loaded["server_url"] == "https://legacy"
