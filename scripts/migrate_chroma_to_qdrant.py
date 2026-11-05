#!/usr/bin/env python3
"""migrate_chroma_to_qdrant.py

One-shot migration of vector data from the deprecated ChromaDB backend to
Qdrant. Reads from each Chroma collection, reshapes payloads, and upserts
into the corresponding Qdrant target:

  Chroma ``odysseus_rag``    → per-user Qdrant ``ody-rag-{sanitize(owner)}``
                               (points with no owner land on ``ody-rag-admin``
                               as legacy bucket)
  Chroma ``vhtna_memories``  → Qdrant ``vhtna_memories`` (shared, owner-tagged)
  Chroma ``vhtna_tool_index``→ Qdrant ``vhtna_tool_index`` (direct copy)

Idempotent: target writes use ``upsert`` so a re-run only re-saves the same
payloads. The default mode is dry-run — pass ``--apply`` to actually write.

Usage::

    python scripts/migrate_chroma_to_qdrant.py            # dry-run, summary only
    python scripts/migrate_chroma_to_qdrant.py --apply    # write to Qdrant

Exit codes:
  0 — success (or dry-run completed without surprises)
  1 — fatal: Chroma source missing / Qdrant unreachable / embedding init failed
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import hashlib
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

# Make ``src.*`` importable when run as a script from the repo root.
_BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _BASE not in sys.path:
    sys.path.insert(0, _BASE)

logger = logging.getLogger("migrate_chroma_to_qdrant")

CHROMA_RAG_COLLECTION = "odysseus_rag"
CHROMA_MEMORY_COLLECTION = "vhtna_memories"
CHROMA_TOOL_INDEX_COLLECTION = "vhtna_tool_index"

ADMIN_FALLBACK_OWNER = "admin"
_BATCH_SIZE = 64


def _sanitize_user_id(user_id: str) -> str:
    """Mirror rag_singleton._sanitize_user_id (collection-name-safe form)."""
    safe = "".join(c if c.isalnum() or c in "._-" else "_" for c in (user_id or ""))
    safe = safe.strip("._-")
    if len(safe) < 3:
        safe = (safe + "________________").ljust(3, "_")
    return safe[:63]


def _per_user_collection(owner: Optional[str]) -> str:
    return f"ody-rag-{_sanitize_user_id(owner or ADMIN_FALLBACK_OWNER)}"


def _get_chroma_client():
    """Connect to Chroma. Soft-fail surfaces a clear message."""
    try:
        import chromadb  # type: ignore
    except ImportError as e:
        raise RuntimeError(
            "chromadb is not installed. Install with: pip install chromadb-client"
        ) from e

    host = os.getenv("CHROMADB_HOST", "localhost")
    port = int(os.getenv("CHROMADB_PORT", "8000"))
    try:
        return chromadb.HttpClient(host=host, port=port)
    except Exception as e:
        raise RuntimeError(
            f"ChromaDB unreachable at {host}:{port}. Start Chroma or set "
            f"CHROMADB_HOST / CHROMADB_PORT. ({e.__class__.__name__}: {e})"
        ) from e


def _get_qdrant():
    from src.qdrant_client import get_qdrant_client
    return get_qdrant_client()


def _get_embedder():
    from src.embeddings import get_embedding_client
    model = get_embedding_client()
    if model is None:
        raise RuntimeError(
            "No embedding backend configured. Set up src/embeddings.py first."
        )
    return model


def _dim_of(embedder) -> int:
    import numpy as np
    probe = embedder.encode(["dim probe"], normalize_embeddings=True)
    return int(np.asarray(probe).shape[-1])


def _ensure_collection(client, name: str, vector_size: int, index_fields: Tuple[str, ...]) -> None:
    from qdrant_client.http import models as qm
    try:
        client.get_collection(collection_name=name)
        return
    except Exception as e:
        status = getattr(e, "status_code", None)
        if status != 404 and "404" not in str(e):
            logger.debug("get_collection(%s) returned %s; attempting create", name, e)

    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )
    for field in index_fields:
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            pass


def _scroll_all_chroma(collection) -> Tuple[List[str], List[List[float]], List[Dict], List[str]]:
    """Return (ids, embeddings, metadatas, documents) for every row."""
    try:
        result = collection.get(include=["embeddings", "metadatas", "documents"])
    except Exception as e:
        logger.warning("collection.get() failed: %s — retrying per-id", e)
        # Some Chroma versions reject include='embeddings' on huge sets. Fall
        # back to plain get() — embeddings may be None, which we re-derive.
        result = collection.get()
    ids = list(result.get("ids") or [])
    embs = list(result.get("embeddings") or [])
    metas = list(result.get("metadatas") or [])
    docs = list(result.get("documents") or [])
    return ids, embs, metas, docs


def _reembed_batch(embedder, texts: List[str]) -> List[List[float]]:
    if not texts:
        return []
    vecs = embedder.encode(texts, normalize_embeddings=True)
    if hasattr(vecs, "tolist"):
        return vecs.tolist()
    return [list(v) for v in vecs]


def _upsert_batch(client, collection_name: str, points) -> None:
    from qdrant_client.http import models as qm
    client.upsert(
        collection_name=collection_name,
        points=[
            qm.PointStruct(id=p["id"], vector=p["vector"], payload=p["payload"])
            for p in points
        ],
        wait=True,
    )


def _migrate_rag(chroma_client, qdrant_client, embedder, dim: int, apply: bool) -> Dict:
    """Split Chroma ``odysseus_rag`` into per-user Qdrant collections."""
    from qdrant_client.http import models as qm

    summary = {"examined": 0, "by_owner": defaultdict(int), "skipped": 0}
    try:
        collection = chroma_client.get_collection(CHROMA_RAG_COLLECTION)
    except Exception as e:
        logger.warning("Chroma collection %s missing: %s — skipping RAG",
                       CHROMA_RAG_COLLECTION, e)
        return summary

    ids, embs, metas, docs = _scroll_all_chroma(collection)
    summary["examined"] = len(ids)

    bucketed: Dict[str, List[Dict]] = defaultdict(list)
    for i, (_id, meta, doc) in enumerate(zip(ids, metas, docs)):
        meta = meta or {}
        owner = (meta.get("owner") or "").strip() or ADMIN_FALLBACK_OWNER
        text = (doc or meta.get("text") or "").strip()
        if not text:
            summary["skipped"] += 1
            continue
        target = _per_user_collection(owner)
        vector = list(embs[i]) if (embs and embs[i] is not None) else None
        payload = {
            "id": _id,
            "text": text,
            "owner": owner,
            "source": meta.get("source") or "migration",
            "type": meta.get("type") or "",
            "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        }
        for k in ("upload_id", "filename", "chunk_id", "title"):
            if meta.get(k) is not None:
                payload[k] = meta[k]
        bucketed[target].append({"id": _id, "vector": vector, "payload": payload,
                                  "text": text})

    if not apply:
        for target, items in bucketed.items():
            logger.info("[dry-run] would write %d points to %s", len(items), target)
        return summary

    # Pre-create target collections (one per owner bucket).
    for target in bucketed:
        _ensure_collection(client=qdrant_client, name=target, vector_size=dim,
                            index_fields=("owner", "source", "type", "upload_id"))

    for target, items in bucketed.items():
        # Fill in any missing vectors by re-embedding.
        texts_missing = [it["text"] for it in items if it["vector"] is None]
        if texts_missing:
            logger.info("Re-embedding %d/%d points for %s (Chroma had no vectors)",
                        len(texts_missing), len(items), target)
            re_vecs = _reembed_batch(embedder, texts_missing)
            vi = 0
            for it in items:
                if it["vector"] is None:
                    it["vector"] = re_vecs[vi]
                    vi += 1

        for start in range(0, len(items), _BATCH_SIZE):
            batch = items[start:start + _BATCH_SIZE]
            _upsert_batch(qdrant_client, target, batch)

        owner_count = sum(1 for it in items
                          if it["payload"].get("owner") != ADMIN_FALLBACK_OWNER) or len(items)
        summary["by_owner"][target] = len(items)
        logger.info("Wrote %d points to %s (real_owner_points=%d)",
                    len(items), target, owner_count)

    return summary


def _migrate_memory(chroma_client, qdrant_client, embedder, dim: int, apply: bool) -> Dict:
    """Migrate ``vhtna_memories`` to Qdrant — owner in payload."""
    summary = {"examined": 0, "written": 0, "skipped": 0}
    collection_name = CHROMA_MEMORY_COLLECTION
    try:
        collection = chroma_client.get_collection(collection_name)
    except Exception as e:
        logger.warning("Chroma collection %s missing: %s — skipping memory",
                       collection_name, e)
        return summary

    ids, embs, metas, docs = _scroll_all_chroma(collection)
    summary["examined"] = len(ids)
    if not ids:
        return summary

    _ensure_collection(qdrant_client, collection_name, dim, index_fields=("owner", "source"))

    prepared = []
    for i, (_id, meta, doc) in enumerate(zip(ids, metas, docs)):
        meta = meta or {}
        text = (doc or meta.get("text") or "").strip()
        if not text:
            summary["skipped"] += 1
            continue
        owner = (meta.get("owner") or "").strip() or ADMIN_FALLBACK_OWNER
        vector = list(embs[i]) if (embs and embs[i] is not None) else None
        payload = {
            "id": _id,
            "text": text,
            "owner": owner,
            "source": meta.get("source") or "memory",
        }
        prepared.append({"id": _id, "vector": vector, "payload": payload, "text": text})

    if not apply:
        logger.info("[dry-run] would write %d points to %s", len(prepared), collection_name)
        return summary

    # Re-embed any rows where Chroma lacked vectors.
    missing = [p for p in prepared if p["vector"] is None]
    if missing:
        vecs = _reembed_batch(embedder, [p["text"] for p in missing])
        for p, v in zip(missing, vecs):
            p["vector"] = v

    for start in range(0, len(prepared), _BATCH_SIZE):
        _upsert_batch(qdrant_client, collection_name, prepared[start:start + _BATCH_SIZE])
    summary["written"] = len(prepared)
    logger.info("Wrote %d memory points to %s", summary["written"], collection_name)
    return summary


def _migrate_tool_index(chroma_client, qdrant_client, embedder, dim: int, apply: bool) -> Dict:
    """Direct-copy ``vhtna_tool_index`` to Qdrant."""
    summary = {"examined": 0, "written": 0, "skipped": 0}
    collection_name = CHROMA_TOOL_INDEX_COLLECTION
    try:
        collection = chroma_client.get_collection(collection_name)
    except Exception as e:
        logger.warning("Chroma collection %s missing: %s — skipping tool_index",
                       collection_name, e)
        return summary

    ids, embs, metas, docs = _scroll_all_chroma(collection)
    summary["examined"] = len(ids)
    if not ids:
        return summary

    _ensure_collection(qdrant_client, collection_name, dim,
                        index_fields=("tool_type", "tool_name", "source"))

    prepared = []
    for i, (_id, meta, doc) in enumerate(zip(ids, metas, docs)):
        meta = meta or {}
        text = (doc or meta.get("text") or "").strip()
        if not text:
            summary["skipped"] += 1
            continue
        vector = list(embs[i]) if (embs and embs[i] is not None) else None
        payload = {
            "id": _id,
            "text": text,
            "tool_name": meta.get("tool_name") or _id,
            "tool_type": meta.get("tool_type") or meta.get("source") or "builtin",
            "source": meta.get("source") or "builtin",
        }
        if meta.get("server_id"):
            payload["server_id"] = meta["server_id"]
        prepared.append({"id": _id, "vector": vector, "payload": payload, "text": text})

    if not apply:
        logger.info("[dry-run] would write %d points to %s", len(prepared), collection_name)
        return summary

    missing = [p for p in prepared if p["vector"] is None]
    if missing:
        vecs = _reembed_batch(embedder, [p["text"] for p in missing])
        for p, v in zip(missing, vecs):
            p["vector"] = v

    for start in range(0, len(prepared), _BATCH_SIZE):
        _upsert_batch(qdrant_client, collection_name, prepared[start:start + _BATCH_SIZE])
    summary["written"] = len(prepared)
    logger.info("Wrote %d tool_index points to %s", summary["written"], collection_name)
    return summary


def main():
    parser = argparse.ArgumentParser(
        description="Migrate Chroma collections → Qdrant (idiomatic, idempotent)."
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Actually write to Qdrant. Without this flag the script is a dry run.",
    )
    parser.add_argument(
        "--only", choices=["rag", "memory", "tool_index"], action="append",
        help="Restrict to a subset (may be given multiple times). Default: all.",
    )
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    logger.info("Mode: %s", "APPLY" if args.apply else "DRY-RUN (no writes)")

    # Soft-fail if Chroma is gone — Qdrant-only deploys have nothing to migrate.
    try:
        chroma_client = _get_chroma_client()
    except RuntimeError as e:
        logger.error("Cannot start migration: %s", e)
        return 1

    try:
        qdrant_client = _get_qdrant()
    except RuntimeError as e:
        logger.error("Qdrant init failed: %s", e)
        return 1

    try:
        embedder = _get_embedder()
        dim = _dim_of(embedder)
    except Exception as e:
        logger.error("Embedding backend init failed: %s", e)
        return 1

    logger.info("Embedding dim = %d", dim)
    targets = args.only or ["memory", "tool_index", "rag"]  # run RAG last

    results = {}
    if "memory" in targets:
        results["memory"] = _migrate_memory(chroma_client, qdrant_client, embedder, dim, args.apply)
    if "tool_index" in targets:
        results["tool_index"] = _migrate_tool_index(chroma_client, qdrant_client, embedder, dim, args.apply)
    if "rag" in targets:
        results["rag"] = _migrate_rag(chroma_client, qdrant_client, embedder, dim, args.apply)

    # Summary
    logger.info("---- Summary ----")
    for kind, r in results.items():
        logger.info("  %s: %s", kind, dict(r))

    return 0


if __name__ == "__main__":
    sys.exit(main())
