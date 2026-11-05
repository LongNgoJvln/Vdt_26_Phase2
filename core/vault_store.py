"""Owner-scoped, Fernet-encrypted vault config persistence.

Replaces the global ``data/vault.json`` that leaked BW_SESSION keys
across users. Each owner's vault config (server URL, email, session,
``unlocked_at``) is JSON-serialized, Fernet-encrypted with the same
key used by ``src/secret_storage`` (so keys are not duplicated), and
stored at ``userdata/<owner>/vault.json.enc`` in MinIO.

Dispatch:

* ``features.infra_enabled("vault_in_minio")`` → MinIO-backed path.
* otherwise → the legacy single-file path at ``routes.vault_routes``.
  ``vault_dual_write`` additionally writes the legacy file for the
  cutover window.

Callers always pass ``owner`` — there is no global bucket. The
``UnconfiguredError`` path returns ``{}`` (caller treats this as "vault
has never been set up") so the absence-vs-empty distinction is
collapsed at the store boundary instead of leaking into route logic.

Security notes
--------------
* BW_SESSION values leave this module only via the returned dict —
  they are never logged (see ``_redact`` below).
* Fernet tokens carry the ``enc:`` prefix from ``secret_storage`` so
  the same rotation / detection utilities apply.
* When MinIO is unreachable under the new path, callers see
  ``{}`` and surface "vault not configured" rather than 500.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core import feature_flags

logger = logging.getLogger(__name__)

# Keys that survive a round-trip. Anything else is dropped at the
# boundary so future callers can't smuggle in stray fields.
_ALLOWED_KEYS = frozenset({
    "server_url", "email", "session", "unlocked_at",
})

_VAULT_OBJECT_KEY = "vault.json.enc"


def _redact(cfg: dict[str, Any]) -> dict[str, Any]:
    """Copy with ``session`` blanked — for logs only."""
    if not cfg:
        return {}
    out = dict(cfg)
    if out.get("session"):
        out["session"] = "<redacted>"
    return out


def _sanitize_in(cfg: dict[str, Any]) -> dict[str, Any]:
    return {k: cfg[k] for k in _ALLOWED_KEYS if k in cfg}


def _minio_enabled() -> bool:
    if not feature_flags.features.infra_enabled("vault_in_minio"):
        return False
    try:
        from src.object_store import store
        return bool(getattr(store, "enabled", False) and getattr(store, "healthy", False))
    except Exception:
        return False


def _dual_write() -> bool:
    return bool(feature_flags.features.infra_enabled("vault_dual_write"))


def _legacy_path() -> Path:
    return Path("data/vault.json")


def _legacy_load() -> dict[str, Any]:
    """Read the legacy global file. Returns ``{}`` on miss/parse error."""
    try:
        p = _legacy_path()
        if not p.exists():
            return {}
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("vault_store legacy read failed: %s", exc)
        return {}


def _legacy_save(cfg: dict[str, Any]) -> None:
    """Write the legacy global file with restrictive perms.

    Used by the dual-write path during the cutover window. After the
    flag becomes default-on, this path is dead code and is removed in
    Phase 2.
    """
    try:
        from core.platform_compat import safe_chmod
        p = _legacy_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        safe_chmod(str(p), 0o600)
    except Exception as exc:  # pragma: no cover — best-effort fallback
        logger.warning("vault_store legacy write failed: %s", exc)


def load(owner: str | None) -> dict[str, Any]:
    """Load the owner-scoped vault config, or ``{}`` if unset.

    Under the legacy path the file is global (cross-tenant); the
    caller is still required to honor owner at the route layer while
    the dual-write window keeps the file alive.
    """
    owner = owner or ""

    if _minio_enabled():
        try:
            from src.object_store import store
            from src import secret_storage
            blob = store.get_user_object(owner, _VAULT_OBJECT_KEY)
            if not blob:
                return {}
            plaintext = secret_storage.decrypt(blob.decode("utf-8"))
            if not plaintext:
                logger.warning("vault_store decrypt returned empty for owner=%s — wrong key?", owner)
                return {}
            data = json.loads(plaintext)
            return _sanitize_in(data) if isinstance(data, dict) else {}
        except Exception as exc:
            logger.warning("vault_store minio load failed for owner=%s: %s", owner, exc)
            # Fall through to legacy if the lookup failed — never 500
            # on secret reads.

    return _sanitize_in(_legacy_load())


def save(owner: str | None, cfg: dict[str, Any]) -> None:
    """Persist the owner-scoped vault config.

    On the MinIO path the plaintext dict is JSON-encoded then
    Fernet-encrypted before upload. On the dual-write path the same
    payload is also written to the legacy file so existing readers
    continue to see updates during the cutover.

    Raises ``RuntimeError`` if MinIO is enabled but unhealthy at write
    time — secrets are NEVER silently dropped to an unconfigured
    bucket.
    """
    owner = owner or ""
    sanitized = _sanitize_in(cfg)

    if _minio_enabled():
        try:
            from src.object_store import store
            from src import secret_storage
            payload = json.dumps(sanitized).encode("utf-8")
            encrypted = secret_storage.encrypt(payload.decode("utf-8"))
            store.put_user_object(
                owner,
                _VAULT_OBJECT_KEY,
                encrypted.encode("utf-8"),
                content_type="application/octet-stream",
            )
        except Exception as exc:
            # Never swallow a secret write failure — the caller must
            # know the unlock did not persist, otherwise the BW_SESSION
            # is in memory only and the next request treats the vault
            # as still locked.
            raise RuntimeError(f"vault_store minio write failed for owner={owner}: {exc}") from exc

        if _dual_write():
            _legacy_save(sanitized)
        return

    # Legacy single-file path. Single-writer design: all admin
    # unlocks append to this file. Acceptable under the confined
    # legacy mode; flag-on path is owner-scoped.
    _legacy_save(sanitized)


def clear_session(owner: str | None) -> None:
    """Remove ``session`` / ``unlocked_at`` from the persisted config."""
    cfg = load(owner)
    cfg.pop("session", None)
    cfg.pop("unlocked_at", None)
    # On dual-write under the legacy path, an admin lock should not
    # destroy another admin's session. This function is only invoked
    # from the owner-scoped route, so it is safe here.
    save(owner, cfg)


def delete(owner: str | None) -> None:
    """Best-effort delete of the owner's vault config record.

    Used by /vault/logout. On the legacy path we just clear session
    fields rather than unlink the file (the file may be shared under
    dual-write).
    """
    if _minio_enabled():
        try:
            from src.object_store import store
            store.delete_user_object(owner or "", _VAULT_OBJECT_KEY)
        except Exception as exc:
            logger.warning("vault_store minio delete failed for owner=%s: %s", owner, exc)
    # Always clear fields on the legacy file too so logout fully
    # strips the session.
    cfg = _legacy_load()
    cfg.pop("session", None)
    cfg.pop("unlocked_at", None)
    if _minio_enabled() and not _dual_write():
        # Legacy file is no longer authoritative under flag-on — skip
        # the write to avoid resurrecting stale state.
        return
    _legacy_save(cfg)
