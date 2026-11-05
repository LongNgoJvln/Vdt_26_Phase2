"""memory_vector.py

Vector index over memory entries, backed by Qdrant.

Shared collection (``vhtna_memories``) across all users. Multi-tenant
isolation is by an ``owner`` payload field:
  - ``add(memory_id, text, owner=...)`` stamps owner on the point.
  - ``search / find_similar / count`` accept ``owner=`` and filter to it.
  - Admin / legacy code passes ``owner=None`` to skip the filter.

Qdrant cosine returns similarity directly (higher = better), so
``score = hit.score`` without any arithmetic.
"""

from __future__ import annotations

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


COLLECTION_NAME = "vhtna_memories"
_BATCH_SIZE = 64
# Match RAG — payload indices for the fields we filter on.
_PAYLOAD_INDEX_FIELDS = ("owner", "source")


def _qdrant_models():
    from qdrant_client.http import models as qm
    return qm


def _ensure_collection(client, name: str, vector_size: int) -> None:
    qm = _qdrant_models()
    try:
        client.get_collection(collection_name=name)
        return
    except Exception as e:
        status = getattr(e, "status_code", None)
        if status != 404 and "404" not in str(e):
            logger.debug(
                "get_collection(%s) returned %s; attempting create", name, e
            )

    existing = {c.name for c in client.get_collections().collections}
    if name in existing:
        return
    client.create_collection(
        collection_name=name,
        vectors_config=qm.VectorParams(size=vector_size, distance=qm.Distance.COSINE),
    )
    for field in _PAYLOAD_INDEX_FIELDS:
        try:
            client.create_payload_index(
                collection_name=name,
                field_name=field,
                field_schema=qm.PayloadSchemaType.KEYWORD,
            )
        except Exception:
            # Index is a perf optimisation; non-fatal if create fails.
            pass


def _owner_filter(owner: Optional[str]):
    if not owner:
        return None
    qm = _qdrant_models()
    return qm.Filter(
        must=[qm.FieldCondition(key="owner", match=qm.MatchValue(value=owner))]
    )


class MemoryVectorStore:
    """Vector index over memory entries for semantic retrieval."""

    COLLECTION_NAME = COLLECTION_NAME

    def __init__(self, data_dir: str, embedding_model=None):
        # ``data_dir`` is ignored under Qdrant — kept for backward-compat
        # with callers that constructed the Chroma version with it.
        self._data_dir = data_dir
        self._model = embedding_model
        self._client = None
        self._dim: Optional[int] = None
        self._healthy = False
        self._initialize()

    def _initialize(self):
        try:
            from src.qdrant_client import get_qdrant_client

            if self._model is None:
                from src.embeddings import get_embedding_client
                self._model = get_embedding_client()
                if self._model is None:
                    raise RuntimeError("No embedding backend available")

            # Probe embedding dim with a single short string — stores it
            # so we can pass it into _ensure_collection on first write.
            probe = self._model.encode(["dim_probe"], normalize_embeddings=True)
            self._dim = int(probe.shape[1]) if hasattr(probe, "shape") else len(probe[0])

            self._client = get_qdrant_client()
            _ensure_collection(self._client, self.COLLECTION_NAME, self._dim)

            self._healthy = True
            logger.info(
                "MemoryVectorStore ready (entries=%s)", self.count()
            )
        except Exception as e:
            logger.error("MemoryVectorStore init failed: %s", e)

    @property
    def healthy(self) -> bool:
        return self._healthy and self._client is not None

    def _embed(self, texts: List[str]) -> List[List[float]]:
        vecs = self._model.encode(texts, normalize_embeddings=True)
        if hasattr(vecs, "tolist"):
            return vecs.tolist()
        return [list(v) for v in vecs]

    def count(self, owner: Optional[str] = None) -> int:
        """Return the number of stored vectors, optionally filtered by owner."""
        if not self.healthy:
            return 0
        try:
            result = self._client.count(
                collection_name=self.COLLECTION_NAME,
                count_filter=_owner_filter(owner),
                exact=True,
            )
            return int(result.count)
        except Exception as e:
            logger.warning("MemoryVectorStore.count failed: %s", e)
            return 0

    def add(self, memory_id: str, text: str, owner: Optional[str] = None) -> None:
        """Add a single memory entry to the vector index.

        ``upsert`` is idempotent on point id, so re-adding the same memory_id
        replaces the previous payload/vector (no need for a pre-check).
        """
        if not self.healthy:
            return
        try:
            qm = _qdrant_models()
            embeddings = self._embed([text])
            payload = {"text": text, "source": "memory", "id": memory_id}
            if owner:
                payload["owner"] = owner
            self._client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    qm.PointStruct(
                        id=memory_id,
                        vector=embeddings[0],
                        payload=payload,
                    )
                ],
                wait=True,
            )
        except Exception as e:
            logger.warning("memory add %s: %s", memory_id, e)

    def clear(self) -> None:
        """Drop every point from the shared collection.

        Used by the admin Danger-Zone wipe. Idempotent — a 404 on the
        collection (fresh Qdrant, never initialised) is logged at debug.
        """
        if not self._client:
            return
        try:
            self._client.delete_collection(collection_name=self.COLLECTION_NAME)
        except Exception as e:
            status = getattr(e, "status_code", None)
            if status != 404 and "404" not in str(e):
                logger.warning("memory clear: delete_collection failed: %s", e)
        # Recreate empty so subsequent writes don't need to re-init.
        if self._dim is not None:
            try:
                _ensure_collection(self._client, self.COLLECTION_NAME, self._dim)
            except Exception as e:
                logger.warning("memory clear: re-init failed: %s", e)

    def remove(self, memory_id: str) -> None:
        """Remove a memory entry. O(1) — no rebuild needed."""
        if not self.healthy:
            return
        try:
            self._client.delete(
                collection_name=self.COLLECTION_NAME,
                points_selector=[memory_id],
                wait=True,
            )
        except Exception as e:
            logger.warning("memory remove %s: %s", memory_id, e)

    def search(
        self, query: str, k: int = 8, owner: Optional[str] = None
    ) -> List[Dict]:
        """Search for the most relevant memory IDs by semantic similarity.

        Returns list of ``{"memory_id": str, "score": float}`` where higher
        score is better. Qdrant cosine returns similarity directly.
        """
        if not self.healthy or self.count(owner=owner) == 0:
            return []

        qm = _qdrant_models()
        embeddings = self._embed([query])
        owner_filter = _owner_filter(owner)

        try:
            resp = self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embeddings[0],
                query_filter=owner_filter,
                limit=k,
                with_payload=True,
            )
            points = resp.points if hasattr(resp, "points") else resp
        except AttributeError:
            # Older qdrant-client: query_points absent — fall back to search.
            points = self._client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=embeddings[0],
                query_filter=owner_filter,
                limit=k,
                with_payload=True,
            )
        except Exception as e:
            logger.warning("memory search failed: %s", e)
            return []

        out = []
        for hit in points:
            mid = (hit.payload or {}).get("id") or str(hit.id)
            score = float(hit.score) if hit.score is not None else 0.0
            out.append({"memory_id": mid, "score": round(score, 4)})
        return out

    def find_similar(
        self,
        text: str,
        threshold: float = 0.92,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """Check if a near-duplicate exists. Returns memory_id if found, else None."""
        if not self.healthy or self.count(owner=owner) == 0:
            return None

        qm = _qdrant_models()
        embeddings = self._embed([text])
        owner_filter = _owner_filter(owner)

        try:
            resp = self._client.query_points(
                collection_name=self.COLLECTION_NAME,
                query=embeddings[0],
                query_filter=owner_filter,
                limit=1,
                with_payload=True,
            )
            points = resp.points if hasattr(resp, "points") else resp
        except AttributeError:
            points = self._client.search(
                collection_name=self.COLLECTION_NAME,
                query_vector=embeddings[0],
                query_filter=owner_filter,
                limit=1,
                with_payload=True,
            )
        except Exception as e:
            logger.warning("memory find_similar failed: %s", e)
            return None

        for hit in points:
            if hit.score is not None and float(hit.score) >= threshold:
                return (hit.payload or {}).get("id") or str(hit.id)
        return None

    def rebuild(self, memories: List[Dict]) -> None:
        """Rebuild the entire index from a list of memory entries.

        Each entry should have ``id`` and ``text`` keys; ``owner`` is
        preserved if present. The shared collection is dropped and recreated
        so stale points don't linger after a wipe.
        """
        if not self._client:
            return

        try:
            self._client.delete_collection(collection_name=self.COLLECTION_NAME)
        except Exception as e:
            # Tolerate 404 — collection may not exist yet on a fresh Qdrant.
            status = getattr(e, "status_code", None)
            if status != 404 and "404" not in str(e):
                logger.debug("delete_collection(%s): %s", self.COLLECTION_NAME, e)

        if self._dim is None:
            probe = self._model.encode(["dim_probe"], normalize_embeddings=True)
            self._dim = int(probe.shape[1]) if hasattr(probe, "shape") else len(probe[0])

        _ensure_collection(self._client, self.COLLECTION_NAME, self._dim)
        self._healthy = True

        qm = _qdrant_models()
        prepared: List[Dict] = []
        for mem in memories:
            text = (mem.get("text") or "").strip()
            mid = mem.get("id") or ""
            if not text or not mid:
                continue
            owner = mem.get("owner")
            try:
                vecs = self._embed([text])
            except Exception as e:
                logger.warning("memory rebuild: skipping %s (embed failed: %s)", mid, e)
                continue
            payload = {"text": text, "source": "memory", "id": mid}
            if owner:
                payload["owner"] = owner
            prepared.append({"id": mid, "vector": vecs[0], "payload": payload})

        for i in range(0, len(prepared), _BATCH_SIZE):
            batch = prepared[i:i + _BATCH_SIZE]
            self._client.upsert(
                collection_name=self.COLLECTION_NAME,
                points=[
                    qm.PointStruct(id=b["id"], vector=b["vector"], payload=b["payload"])
                    for b in batch
                ],
                wait=True,
            )

        logger.info("MemoryVectorStore rebuilt with %s entries", len(prepared))
