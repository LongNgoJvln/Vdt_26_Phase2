"""src/user_workspace.py

Per-user path/key resolvers. Every tenant's data lives under a per-user
prefix — ``userdata/{user_id}/...`` — whether on minIO or local FS.
"""

from __future__ import annotations

import logging
import os
from typing import List, Optional

from src.constants import DATA_DIR

logger = logging.getLogger(__name__)


def user_root(user_id: str) -> str:
    """Per-user root key/prefix (no trailing slash)."""
    return f"userdata/{user_id}"


def docs_prefix(user_id: str) -> str:
    """Per-user docs prefix used on minIO and local FS alike."""
    return f"{user_root(user_id)}/docs"


def rag_prefix(user_id: str) -> str:
    """Per-user RAG prefix."""
    return f"{user_root(user_id)}/rag"


def local_user_dir(user_id: str, *parts: str) -> str:
    """Build a local-filesystem path under ``{DATA_DIR}/userdata/{user_id}/...``.

    Creates parent directories as needed so callers can ``open(path, 'wb')``
    directly.
    """
    base = os.path.join(DATA_DIR, "userdata", user_id, *map(_safe_part, parts))
    os.makedirs(os.path.dirname(base) or ".", exist_ok=True)
    return base


def _safe_part(name: str) -> str:
    """Strip path separators so a part can't escape its parent."""
    return name.replace("/", "_").replace("\\", "_").lstrip(".") or "unnamed"


def ensure_user_workspace(user_id: str, store) -> str:
    """Bootstrap a per-user working directory.

    Creates local sub-dirs under ``{DATA_DIR}/userdata/{user_id}/``:
    ``library/``, ``sessions/``, ``brains/``, ``cache/``.

    Verifies the MinIO prefix is accessible when the store is healthy.

    Returns the local working directory path.
    """
    if not user_id:
        raise ValueError("user_id is required")

    work_dir = os.path.join(DATA_DIR, "userdata", user_id)
    for sub in ("library", "sessions", "brains", "cache"):
        os.makedirs(os.path.join(work_dir, sub), exist_ok=True)

    if store and getattr(store, "healthy", False):
        try:
            prefix = user_root(user_id)
            list(store._client.list_objects(
                bucket_name=store._client._BUCKET if hasattr(store._client, '_BUCKET') else None,
                prefix=prefix,
            ))
            logger.info(
                "ensure_user_workspace: minIO accessible for user=%s prefix=%s",
                user_id, prefix,
            )
        except Exception as exc:
            logger.warning(
                "ensure_user_workspace: minIO access failed for user=%s: %s",
                user_id, exc,
            )

    logger.info("ensure_user_workspace: ready for user=%s dir=%s", user_id, work_dir)
    return work_dir


def sync_user_workspace(user_id: str, store) -> None:
    """Pull per-user data from MinIO into the local working directory.

    Syncs ``library/``, ``sessions/``, and ``brains/`` prefixes. Runs in
    the background after login — should never block the response path.
    """
    if not user_id:
        return

    if not store or not getattr(store, "healthy", False):
        logger.info(
            "sync_user_workspace: minIO disabled, skipping sync for user=%s",
            user_id,
        )
        return

    work_dir = os.path.join(DATA_DIR, "userdata", user_id)

    for sub in ("library", "sessions", "brains"):
        try:
            _sync_prefix(store, user_id, sub, work_dir)
        except Exception as exc:
            logger.warning(
                "sync_user_workspace: failed for user=%s prefix=%s: %s",
                user_id, sub, exc,
            )


def _sync_prefix(store, user_id: str, sub: str, work_dir: str) -> None:
    """Pull all objects under ``userdata/{user_id}/{sub}/`` to local disk."""
    prefix = f"{user_root(user_id)}/{sub}/"
    bucket = None
    try:
        # Determine bucket from store internals (matching chat_processor pattern)
        bucket = os.getenv("MINIO_BUCKET", "ody-userdata")
    except Exception:
        pass

    try:
        objects = list(store._client.list_objects(
            bucket_name=bucket,
            prefix=prefix,
            recursive=True,
        ))
    except Exception as exc:
        logger.warning(
            "_sync_prefix: list failed for user=%s prefix=%s: %s",
            user_id, prefix, exc,
        )
        return

    if not objects:
        return

    local_subdir = os.path.join(work_dir, sub)
    os.makedirs(local_subdir, exist_ok=True)

    for obj in objects:
        try:
            data = store._client.get_object(bucket, obj.object_name)
            try:
                raw = data.read()
            finally:
                data.close()
                data.release_conn()
        except Exception as exc:
            logger.warning(
                "_sync_prefix: get failed for %s: %s",
                obj.object_name, exc,
            )
            continue

        # obj.object_name is the full key: userdata/{user}/{sub}/{name}
        rel = obj.object_name[len(prefix):]
        if not rel:
            continue
        # Sanitize: only allow filenames, no further slashes
        if "/" in rel:
            # nested key — preserve sub-paths under local_subdir
            parts = [_safe_part(p) for p in rel.split("/") if p]
            local_path = os.path.join(local_subdir, *parts)
        else:
            local_path = os.path.join(local_subdir, _safe_part(rel))

        os.makedirs(os.path.dirname(local_path) or ".", exist_ok=True)
        try:
            with open(local_path, "wb") as f:
                f.write(raw)
            logger.debug(
                "_sync_prefix: synced %s -> %s (%s bytes)",
                obj.object_name, local_path, len(raw),
            )
        except Exception as exc:
            logger.warning(
                "_sync_prefix: local write failed for %s: %s",
                local_path, exc,
            )
