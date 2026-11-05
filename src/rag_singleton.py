"""
rag_singleton.py

Per-user lazy initializer for Qdrant-backed VectorRAG.

The first call for a given user creates and caches a VectorRAG instance
with its own collection (``ody-rag-{user_id}``) and per-user persist
directory (``data/userdata/{user_id}/rag``). Failed inits are throttled
to one retry per user per ``_RETRY_INTERVAL`` seconds.

Calling without a ``user_id`` returns the legacy global collection so
older unauth/legacy data remains searchable.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

_BASE_DIR = Path(__file__).parent.parent
_LOCAL_RAG_ROOT = _BASE_DIR / "data" / "userdata"

_LEGACY_PERSIST_DIR = _BASE_DIR / "data" / "rag"
_LEGACY_COLLECTION = "odysseus_rag"

# Per-user cache: user_id -> VectorRAG
_instances: dict[str, "VectorRAG"] = {}
_last_attempt: dict[str, float] = {}
_retry_interval = 30  # seconds between re-init attempts per user

# Legacy (no user_id) singleton
_legacy_instance: Optional["VectorRAG"] = None
_legacy_last_attempt = 0.0

_lock = threading.Lock()


def _build_for_user(user_id: str):
    """Construct a VectorRAG scoped to ``user_id``."""
    from src.rag_vector import VectorRAG

    # Per-user persist dir: data/userdata/{user_id}/rag
    persist_dir = os.path.join(_LOCAL_RAG_ROOT, user_id, "rag")
    collection = f"ody-rag-{_sanitize_user_id(user_id)}"
    return VectorRAG(persist_directory=persist_dir, collection_name=collection)


def _sanitize_user_id(user_id: str) -> str:
    """Chroma collection names must be 3-63 chars, [a-zA-Z0-9._-]."""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in user_id)
    safe = safe.strip("._-")
    if len(safe) < 3:
        safe = (safe + "________________").ljust(3, "_")
    return safe[:63]


def get_rag_manager_for_user(user_id: Optional[str] = None):
    """Return a VectorRAG instance for ``user_id``, creating it lazily.

    - ``user_id`` provided: per-user collection + persist directory.
    - ``user_id`` None: legacy global collection (``odysseus_rag``).

    Returns None if Qdrant isn't reachable.
    """
    global _legacy_instance, _legacy_last_attempt

    if user_id is None:
        if _legacy_instance is not None:
            return _legacy_instance
        now = time.monotonic()
        if now - _legacy_last_attempt < _retry_interval:
            return None
        _legacy_last_attempt = now
        try:
            from src.rag_vector import VectorRAG

            _legacy_instance = VectorRAG(
                persist_directory=_LEGACY_PERSIST_DIR,
                collection_name=_LEGACY_COLLECTION,
            )
            if not _legacy_instance.healthy:
                logger.warning("Legacy VectorRAG created but not healthy")
                _legacy_instance = None
            else:
                logger.info("Initialized legacy VectorRAG")
        except Exception as exc:
            logger.warning(f"Legacy VectorRAG init failed: {exc}")
            _legacy_instance = None
        return _legacy_instance

    with _lock:
        existing = _instances.get(user_id)
        if existing is not None:
            return existing

        now = time.monotonic()
        last = _last_attempt.get(user_id, 0.0)
        if now - last < _retry_interval:
            return None
        _last_attempt[user_id] = now

        try:
            instance = _build_for_user(user_id)
        except Exception as exc:
            logger.warning(f"VectorRAG init failed for user={user_id}: {exc}")
            return None

        if not instance.healthy:
            logger.warning(f"VectorRAG created but not healthy for user={user_id}")
            return None

        _instances[user_id] = instance
        logger.info(f"Initialized VectorRAG for user={user_id}")
        return instance


# Backward-compatible alias. Old callers used ``get_rag_manager()`` with
# no arguments to get the legacy global instance.
def get_rag_manager():
    return get_rag_manager_for_user(user_id=None)
