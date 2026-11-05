"""User preferences API — per-user key/value store.

Backend dispatches between two stores:

* Legacy: ``data/user_prefs.json`` with a ``_users`` block — single
  cross-tenant blob, whole-file rewrite on every per-key update.
* DB: the ``user_settings`` table (keyed ``(owner, key)``) — physical
  per-tenant separation, O(1) per-key writes.

The DB path is gated on both ``user_settings_in_db`` AND
``multitenant_postgres`` infra flags. Under ``user_settings_dual_write``
the JSON blob is also written so cuts over can be reversed.
"""
import json
import os
import logging
from typing import Optional
from fastapi import APIRouter, Request
from src.auth_helpers import get_current_user
from core import feature_flags

logger = logging.getLogger(__name__)

PREFS_FILE = os.path.join("data", "user_prefs.json")


def _load():
    """Load the raw prefs file (internal use only)."""
    try:
        with open(PREFS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def _save(prefs):
    os.makedirs(os.path.dirname(PREFS_FILE), exist_ok=True)
    with open(PREFS_FILE, "w", encoding="utf-8") as f:
        json.dump(prefs, f, indent=2)


# ── DB dispatch helpers (user_settings_in_db) ──────────────────────────

def _db_user_settings_enabled() -> bool:
    return bool(
        feature_flags.features.infra_enabled("user_settings_in_db")
        and feature_flags.features.infra_enabled("multitenant_postgres")
    )


def _db_dual_write() -> bool:
    return bool(feature_flags.features.infra_enabled("user_settings_dual_write"))


def _db_load_for_user(owner: str) -> dict:
    """SELECT all ``(key, value_json)`` rows for owner; decode each value."""
    from core.database import UserSetting, SessionLocal
    out: dict = {}
    with SessionLocal() as db:
        rows = db.query(UserSetting).filter(UserSetting.owner == owner).all()
        for r in rows:
            try:
                out[r.key] = json.loads(r.value_json)
            except (json.JSONDecodeError, TypeError):
                logger.warning("Skipping corrupt user_settings row owner=%s key=%s", owner, r.key)
    return out


def _db_upsert_key(owner: str, key: str, value) -> None:
    from core import db_upsert
    from core.database import UserSetting, SessionLocal
    with SessionLocal() as db:
        db_upsert.upsert(
            db,
            UserSetting,
            ["owner", "key"],
            {
                "owner": owner,
                "key": key,
                "value_json": json.dumps(value),
            },
            update_columns=["value_json"],
        )
        db.commit()


def _db_delete_key(owner: str, key: str) -> None:
    from core.database import UserSetting, SessionLocal
    with SessionLocal() as db:
        db.query(UserSetting).filter(
            UserSetting.owner == owner, UserSetting.key == key
        ).delete(synchronize_session=False)
        db.commit()


def _db_delete_user(owner: str) -> int:
    from core.database import UserSetting, SessionLocal
    with SessionLocal() as db:
        count = (
            db.query(UserSetting)
            .filter(UserSetting.owner == owner)
            .delete(synchronize_session=False)
        )
        db.commit()
        return int(count or 0)


def _db_rename_user(old_owner: str, new_owner: str) -> int:
    """Re-bind all rows from old_owner to new_owner. Collisions on
    the ``(owner, key)`` unique constraint are not expected under normal
    rename flow (auth_routes rejects rename when new username exists)
    but if any row does collide the call surfaces IntegrityError so the
    caller can roll back to the JSON path."""
    from core.database import UserSetting, SessionLocal
    with SessionLocal() as db:
        count = (
            db.query(UserSetting)
            .filter(UserSetting.owner == old_owner)
            .update({UserSetting.owner: new_owner}, synchronize_session=False)
        )
        db.commit()
        return int(count or 0)


def rename_user(old_username: str, new_username: str) -> int:
    """Rename a user's prefs across both backends.

    Returns the count of DB rows moved (0 when the DB flag is off).
    The JSON blob is touched unconditionally so the dual-write invariant
    holds during cutover.
    """
    moved = 0
    if _db_user_settings_enabled():
        try:
            moved = _db_rename_user(old_username, new_username)
        except Exception as e:
            logger.error("Failed to rename user_settings rows %s->%s: %s", old_username, new_username, e)
    try:
        prefs = _load()
        users = prefs.get("_users") if isinstance(prefs, dict) else None
        if isinstance(users, dict):
            prefs_key = next(
                (k for k in users if str(k).strip().lower() == old_username),
                None,
            )
            new_taken = any(str(k).strip().lower() == new_username for k in users)
            if prefs_key is not None and not new_taken:
                users[new_username] = users.pop(prefs_key)
                _save(prefs)
    except Exception as e:
        logger.warning("Failed to rename user prefs JSON %s -> %s: %s", old_username, new_username, e)
    return moved


def delete_user(username: str) -> int:
    """Drop a user's prefs across both backends. Called from the
    delete-user flow; returns the DB row count removed (0 when the flag
    is off)."""
    removed = 0
    if _db_user_settings_enabled():
        try:
            removed = _db_delete_user(username)
        except Exception as e:
            logger.error("Failed to delete user_settings rows for %s: %s", username, e)
    try:
        prefs = _load()
        users = prefs.get("_users") if isinstance(prefs, dict) else None
        if isinstance(users, dict):
            prefs_key = next(
                (k for k in users if str(k).strip().lower() == username),
                None,
            )
            if prefs_key is not None:
                users.pop(prefs_key, None)
                _save(prefs)
    except Exception as e:
        logger.warning("Failed to delete user prefs JSON for %s: %s", username, e)
    return removed


# ── Dispatch entry points ──────────────────────────────────────────────

def _load_for_user(user: Optional[str] = None) -> dict:
    """Load preferences for a specific user.

    When the DB flag is on, ``user`` must be a non-empty username — the
    per-user table has no row for the legacy "auth disabled" sentinel so
    we fall through to the JSON blob in that case (preserves the existing
    behavior for auth-deferred boots).
    """
    if _db_user_settings_enabled() and user:
        try:
            return _db_load_for_user(user)
        except Exception as e:
            logger.error("Failed to load user_settings for %s: %s", user, e)
            # Fall through to legacy so a DB outage doesn't lock users
            # out of their prefs entirely.
    all_prefs = _load()
    if "_users" in all_prefs:
        if user is None:
            users = all_prefs["_users"]
            return dict(next(iter(users.values()), {}))
        return dict(all_prefs["_users"].get(user, {}))
    return dict(all_prefs)


def _save_for_user(user: Optional[str], prefs: dict):
    """Save the full prefs dict for a user.

    Under the DB flag this rewrites every per-user row to match the
    supplied dict — keys absent from ``prefs`` are deleted, keys present
    are upserted. The JSON blob is also rewritten under dual-write.
    """
    if _db_user_settings_enabled() and user:
        try:
            existing = _db_load_for_user(user)
            for key, value in prefs.items():
                if existing.get(key) != value:
                    _db_upsert_key(user, key, value)
            stale = set(existing) - set(prefs)
            for key in stale:
                _db_delete_key(user, key)
            if not _db_dual_write():
                return
        except Exception as e:
            logger.error("Failed to persist user_settings for %s: %s", user, e)
            # Fall through to JSON write so the request doesn't 500.
    all_prefs = _load()
    if user is None:
        _save(prefs)
        return
    if "_users" not in all_prefs:
        all_prefs = {"_users": {}}
    all_prefs["_users"][user] = prefs
    _save(all_prefs)


def setup_prefs_routes():
    router = APIRouter(prefix="/api/prefs", tags=["preferences"])

    @router.get("")
    async def get_all_prefs(request: Request):
        user = get_current_user(request)
        return _load_for_user(user)

    @router.get("/{key}")
    async def get_pref(request: Request, key: str):
        user = get_current_user(request)
        prefs = _load_for_user(user)
        return {"key": key, "value": prefs.get(key)}

    @router.put("/{key}")
    async def set_pref(request: Request, key: str, body: dict):
        user = get_current_user(request)
        prefs = _load_for_user(user)
        prefs[key] = body.get("value")
        _save_for_user(user, prefs)
        return {"key": key, "value": prefs[key]}

    return router
