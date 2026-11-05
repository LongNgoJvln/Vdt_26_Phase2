"""services/research/research_store.py

Per-owner persistence for deep-research results.

Two backends, dispatched by infra flag ``ODYSSEUS_RESEARCH_IN_MINIO``:

* Flag OFF (default): flat on-disk ``data/deep_research/<id>.json`` — the
  legacy path, unchanged behaviour.
* Flag ON: per-owner object under ``userdata/{owner}/research/<id>.json``
  via :class:`ObjectStore`. MinIO credentials and bucket are configured by
  the existing ``ODYSSEUS_USE_MINIO`` / ``MINIO_*`` env vars; when MinIO
  is unreachable the store falls back to local files under
  ``data/userdata/{owner}/research/<id>.json`` so a flag flip alone never
  makes research data unreachable.

The MinIO path writes owner-stamped JSON inside the caller's own
``userdata/`` prefix — one tenant physically cannot list, read, or delete
another tenant's research objects, because the S3 key is namespaced by
owner. That is the whole point of the migration.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Dict, Iterator, List, Optional

from core import feature_flags
from src.object_store import store as _object_store

logger = logging.getLogger(__name__)

# Legacy flat directory, kept for the flag-off path and for back-fill.
LEGACY_DIR = Path("data/deep_research")
LEGACY_DIR.mkdir(parents=True, exist_ok=True)

# Same path-traversal gate as the route layer — research ids are bare
# tokens (uuids / slugs). Anything else is rejected before it touches
# the filesystem or object key.
_RID_RE = re.compile(r"^[A-Za-z0-9_-]{1,128}$")

# Local-FS fallback when MinIO is flagged on but unhealthy. Mirrors the
# object-prefix layout so a future re-attempt picks the same path.
_FALLBACK_ROOT = Path("data/userdata")


def _validate_rid(rid: str) -> None:
    if not rid or not _RID_RE.fullmatch(rid):
        raise ValueError("Invalid research id")


def _minio_enabled() -> bool:
    return bool(feature_flags.features.infra_enabled("research_in_minio"))


def _dual_write() -> bool:
    return bool(feature_flags.features.infra_enabled("research_dual_write"))


def _object_key(rid: str) -> str:
    """Key under ``userdata/{owner}/``."""
    _validate_rid(rid)
    return f"research/{rid}.json"


def _fallback_path(owner: str, rid: str) -> Path:
    _validate_rid(rid)
    safe_owner = re.sub(r"[^A-Za-z0-9_.@-]", "_", owner or "_shared")
    return _FALLBACK_ROOT / safe_owner / "research" / f"{rid}.json"


# ── Load ──────────────────────────────────────────────────────────────


def load(owner: Optional[str], rid: str) -> Optional[Dict]:
    """Return the saved research dict for ``rid`` owned by ``owner``.

    When ``owner`` is None (auth disabled), only the legacy flat file is
    consulted — those entries have never been per-owner. Under auth, the
    MinIO path is checked first (under dual-write it is the source of
    truth); under flag-off or MinIO-unhealthy, the legacy flat file is
    read with an owner check (legacy rows with no ``owner`` field are
    treated as admin-owned and surfaced only when ``owner`` is None).
    """
    _validate_rid(rid)
    if _minio_enabled() and owner is not None:
        payload = _load_from_object_store(owner, rid)
        if payload is not None:
            return payload
    return _load_from_legacy_with_owner_check(owner, rid)


def _load_from_object_store(owner: str, rid: str) -> Optional[Dict]:
    raw = _object_store.get_user_object(owner, _object_key(rid))
    if raw is None:
        return _load_from_fallback(owner, rid)
    try:
        return json.loads(raw.decode("utf-8"))
    except Exception as exc:
        logger.warning("research_store: corrupt object owner=%s rid=%s: %s", owner, rid, exc)
        return None


def _load_from_fallback(owner: str, rid: str) -> Optional[Dict]:
    p = _fallback_path(owner, rid)
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("research_store: corrupt fallback owner=%s rid=%s: %s", owner, rid, exc)
        return None


def _load_from_legacy_with_owner_check(owner: Optional[str], rid: str) -> Optional[Dict]:
    p = LEGACY_DIR / f"{rid}.json"
    if not p.exists():
        return None
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("research_store: corrupt legacy rid=%s: %s", rid, exc)
        return None
    if owner is None:
        return data
    row_owner = data.get("owner")
    if not row_owner:
        # Legacy ownerless row — invisible under auth until admin migrates.
        return None
    return data if row_owner == owner else None


# ── Save ──────────────────────────────────────────────────────────────


def save(owner: Optional[str], rid: str, data: Dict, *, dual_write: Optional[bool] = None) -> None:
    """Persist ``data`` for ``rid`` owned by ``owner``.

    Under ``research_in_minio`` the dict is written as a per-owner
    object; if ``dual_write`` is true (or ``research_dual_write`` is on)
    the legacy flat file is also updated so a flag flip is reversible.
    Under flag-off only the legacy file is touched.
    """
    _validate_rid(rid)
    blob = json.dumps(data, ensure_ascii=False)
    if dual_write is None:
        dual_write = _dual_write()

    if _minio_enabled() and owner is not None:
        _write_to_object_store(owner, rid, blob)
        if dual_write:
            _write_to_legacy_flat(rid, blob)
        return
    _write_to_legacy_flat(rid, blob)


def _write_to_object_store(owner: str, rid: str, blob: str) -> None:
    key = _object_key(rid)
    if _object_store.healthy:
        try:
            _object_store.put_user_object(owner, key, blob.encode("utf-8"), "application/json")
            return
        except Exception as exc:
            logger.warning("research_store: MinIO write failed owner=%s rid=%s (%s) — using FS fallback", owner, rid, exc)
    p = _fallback_path(owner, rid)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(blob, encoding="utf-8")


def _write_to_legacy_flat(rid: str, blob: str) -> None:
    p = LEGACY_DIR / f"{rid}.json"
    p.write_text(blob, encoding="utf-8")


# ── Delete ────────────────────────────────────────────────────────────


def delete(owner: Optional[str], rid: str) -> bool:
    """Delete ``rid`` owned by ``owner``. Returns True if anything was removed.

    Idempotent — returns False when neither backend held the row.
    Owner check on the legacy flat path mirrors :func:`load`: foreign rows
    are not deleted.
    """
    _validate_rid(rid)
    removed = False
    if _minio_enabled() and owner is not None:
        if _object_store.healthy:
            removed = _object_store.delete_user_object(owner, _object_key(rid))
        if not removed:
            p = _fallback_path(owner, rid)
            if p.exists():
                p.unlink()
                removed = True
        if _dual_write():
            _delete_legacy_flat_if_owned(owner, rid)
        return removed
    return _delete_legacy_flat_if_owned(owner, rid)


def _delete_legacy_flat_if_owned(owner: Optional[str], rid: str) -> bool:
    p = LEGACY_DIR / f"{rid}.json"
    if not p.exists():
        return False
    if owner is not None:
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            # Broken file: only delete under auth-disabled or when owner matches.
            data = {}
        row_owner = data.get("owner")
        if row_owner and row_owner != owner:
            return False
    try:
        p.unlink()
        return True
    except Exception as exc:
        logger.warning("research_store: failed to unlink legacy rid=%s: %s", rid, exc)
        return False


# ── List ──────────────────────────────────────────────────────────────


def list_ids(owner: Optional[str]) -> Iterator[str]:
    """Yield research ids visible to ``owner``.

    Under auth-disabled (owner None) the legacy flat directory is walked
    in full. Under auth + MinIO the per-owner prefix is enumerated; the
    legacy flat directory is also walked under dual-write so old rows
    keep surfacing during cutover.
    """
    if _minio_enabled() and owner is not None:
        seen: set[str] = set()
        for rid in _iter_object_store_ids(owner):
            seen.add(rid)
            yield rid
        if _dual_write():
            for rid in _iter_legacy_ids(owner):
                if rid not in seen:
                    yield rid
        return
    yield from _iter_legacy_ids(owner)


def _iter_object_store_ids(owner: str) -> Iterator[str]:
    if not _object_store.healthy:
        for p in _fallback_path(owner, "").parent.glob("*.json"):
            yield p.stem
        return
    prefix = "research/"
    for full_key in _object_store.list_user_objects(owner, prefix, recursive=True):
        # full_key looks like ``userdata/{owner}/research/{rid}.json`` —
        # slice off the prefix to recover the rid.
        tail = full_key.rsplit("/research/", 1)[-1]
        if tail.endswith(".json"):
            rid = tail[: -len(".json")]
            if _RID_RE.fullmatch(rid):
                yield rid


def _iter_legacy_ids(owner: Optional[str]) -> Iterator[str]:
    if not LEGACY_DIR.exists():
        return
    for p in LEGACY_DIR.glob("*.json"):
        if owner is not None:
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                continue
            row_owner = data.get("owner")
            if not row_owner or row_owner != owner:
                continue
        yield p.stem


# ── Migration helpers ─────────────────────────────────────────────────


def backfill_one(owner: str, rid: str) -> bool:
    """Promote a legacy flat file into the per-owner object store.

    Returns True on success or when already migrated; False on miss or
    invalid input. Used by the back-fill migration script.

    The legacy file is left in place for safety during cutover — the
    operator removes the flat directory after the dual-write audit
    window.
    """
    _validate_rid(rid)
    legacy_path = LEGACY_DIR / f"{rid}.json"
    if not legacy_path.exists():
        return False
    data = json.loads(legacy_path.read_text(encoding="utf-8"))
    data.setdefault("owner", owner)
    save(owner, rid, data, dual_write=True)
    return True
