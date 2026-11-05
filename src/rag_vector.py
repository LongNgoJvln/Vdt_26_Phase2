"""rag_vector.py

Vector-based RAG backed by Qdrant. Hybrid retrieval: 70% cosine similarity
+ 30% keyword overlap.

Qdrant notes:
  - Cosine returns similarity (higher = better), not distance — so
    ``vector_sim = hit.score`` is the only arithmetic needed.
  - Payload holds the text (Qdrant has no separate "document" field like
    Chroma's). ``payload["text"]`` is the canonical field on every point.
  - Per-user collections are the multi-tenant boundary (one collection
    per owner). The collection factory lives in src/rag_singleton.py.
  - Payload indices on ``owner``, ``source``, ``type`` keep filters cheap.
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger(__name__)

DEFAULT_FILE_EXTENSIONS: Set[str] = {
    '.txt', '.md', '.markdown', '.py', '.json', '.yaml', '.yml',
    '.csv', '.html', '.htm', '.css', '.js', '.pdf',
    '.docx', '.pptx', '.xlsx', '.xls', '.epub',
}

VECTOR_WEIGHT = 0.7
KEYWORD_WEIGHT = 0.3

COLLECTION_NAME = "odysseus_rag"

# Bumped any time the payload schema changes; used by ensure_collection to
# decide whether we need to (re)create payload indices. Idempotent.
_PAYLOAD_INDEX_FIELDS = ("owner", "source", "type", "upload_id")
_BATCH_SIZE = 64


def _sanitize_owner_for_id(owner: Optional[str]) -> str:
    if not owner:
        return "_legacy"
    cleaned = re.sub(r"[^A-Za-z0-9_.-]", "_", owner).strip("._-")
    return cleaned[:48] or "_legacy"


def _generate_doc_id(text: str, owner: Optional[str] = None) -> str:
    """Deterministic UUID per (owner, text).

    Qdrant 1.18 only accepts point IDs that are either unsigned integers
    or UUIDs — strings like ``vht_doc_<hex>`` get rejected with 400. We
    use UUID5 (namespace from owner, name from sha256 of text) so:
      * Same (owner, content) → same UUID. Idempotent re-ingest / dedupe.
      * Different owners with identical text → different IDs.
    """
    ns_hex = hashlib.sha256(_sanitize_owner_for_id(owner).encode("utf-8")).digest()[:16]
    namespace = uuid.UUID(bytes=ns_hex)
    name = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return str(uuid.uuid5(namespace, name))


# ---------------------------------------------------------------------------
# Lightweight Qdrant client helpers
# ---------------------------------------------------------------------------

def _qdrant_models():
    from qdrant_client.http import models as qm
    return qm


def _ensure_collection(client, name: str, vector_size: int) -> None:
    """Idempotent collection create + payload index setup."""
    qm = _qdrant_models()
    try:
        client.get_collection(collection_name=name)
        return
    except Exception as e:
        # 404 means missing — fall through and create. Any other error
        # ( transport, auth) means we shouldn't silently retry; raise.
        status = getattr(e, "status_code", None)
        if status != 404 and "404" not in str(e):
            # If this was a transient error on an existing collection, the
            # subsequent reads will fail loudly anyway. Tolerate and try
            # the create path.
            logger.debug("get_collection(%s) returned %s; attempting create", name, e)

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
            # Indexed payloads are a perf optimisation; if creating the
            # index fails (e.g. already exists, version mismatch) the
            # collection still works — just slower on filtered queries.
            pass


def _owner_filter(owner: Optional[str]):
    qm = _qdrant_models()
    if owner is None:
        return None
    return qm.Filter(must=[qm.FieldCondition(key="owner", match=qm.MatchValue(value=owner))])


def _source_filter(source: str):
    qm = _qdrant_models()
    return qm.Filter(must=[qm.FieldCondition(key="source", match=qm.MatchValue(value=source))])


def _count(client, collection_name: str, owner: Optional[str] = None) -> int:
    try:
        resp = client.count(
            collection_name=collection_name,
            count_filter=_owner_filter(owner),
            exact=True,
        )
        return resp.count
    except Exception as e:
        status = getattr(e, "status_code", None)
        # 404 = collection doesn't exist yet (count == 0 from caller's POV).
        if status == 404 or "404" in str(e):
            return 0
        raise


class VectorRAG:
    """Per-user RAG backed by a single Qdrant collection."""

    def __init__(
        self,
        persist_directory: str = "data/chroma",
        collection_name: str = COLLECTION_NAME,
    ):
        # persist_directory was a Chroma SQLite path; kept for signature
        # compat with rag_singleton.VectorRAG factory. Qdrant is remote so
        # we ignore it.
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self._client = None
        self._model = None
        self._healthy = False
        self._dim: Optional[int] = None

        self._initialize_system()

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize_system(self) -> bool:
        try:
            from src.qdrant_client import get_qdrant_client
            from src.embeddings import get_embedding_client

            self._model = get_embedding_client()
            if self._model is None:
                raise RuntimeError("No embedding backend available")
            logger.info(
                "Embedding: %s model=%s", getattr(self._model, "url", "local"),
                getattr(self._model, "model", "n/a"),
            )

            self._client = get_qdrant_client()
            # Probe embedding dim by encoding one short sentence — matches the
            # vector dim Qdrant must be configured with.
            dims = self._model.encode(["dim probe"], normalize_embeddings=True)
            import numpy as np  # local import — only needed at init
            self._dim = int(np.asarray(dims).shape[-1])

            _ensure_collection(self._client, self.collection_name, self._dim)
            count = _count(self._client, self.collection_name)
            logger.info("VectorRAG ready (collection=%s, %d docs)", self.collection_name, count)
            self._healthy = True
            return True
        except Exception as e:
            logger.error("VectorRAG init failed: %s", e)
            self._healthy = False
            return False

    def _embed(self, texts: List[str]) -> List[List[float]]:
        import numpy as np
        vecs = self._model.encode(texts, normalize_embeddings=True)
        return np.array(vecs, dtype=np.float32).tolist()

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def healthy(self) -> bool:
        return self._healthy and self._client is not None

    @property
    def collection(self):
        """Compatibility shim — historically returned the Chroma collection.

        Nothing internal should call this after the migration. We surface
        the Qdrant client so external adapters (personal_routes etc.) get
        an object with real behavior rather than None. Callers that needed
        Chroma-specific APIs must be ported.
        """
        return self._client

    # ------------------------------------------------------------------
    # Document operations
    # ------------------------------------------------------------------

    def add_document(self, text: str, metadata: Dict[str, Any]) -> bool:
        if not self.healthy:
            logger.error("VectorRAG not initialized")
            return False
        if not text or not isinstance(text, str):
            return False
        if not metadata or not isinstance(metadata, dict):
            return False

        try:
            qm = _qdrant_models()
            doc_id = _generate_doc_id(text, metadata.get('owner'))
            embeddings = self._embed([text])
            payload = {**metadata, "text": text, "id": doc_id}
            self._client.upsert(
                collection_name=self.collection_name,
                points=[qm.PointStruct(id=doc_id, vector=embeddings[0], payload=payload)],
                wait=True,
            )
            return True
        except Exception as e:
            logger.error("add_document failed: %s", e)
            return False

    def add_documents_batch(self, docs: List[tuple]) -> Dict[str, Any]:
        if not self.healthy:
            return {"success": False, "message": "VectorRAG not initialized"}
        if not docs:
            return {"success": False, "message": "Empty document list"}

        valid = [
            (t, m) for t, m in docs
            if t and isinstance(t, str) and m and isinstance(m, dict)
        ]
        if not valid:
            return {"success": False, "message": "No valid documents"}

        try:
            qm = _qdrant_models()
            texts = [t for t, _ in valid]
            metas = [m for _, m in valid]
            ids = [_generate_doc_id(t, m.get('owner')) for t, m in valid]
            embeddings = self._embed(texts)

            written = 0
            for i in range(0, len(texts), _BATCH_SIZE):
                batch_ids = ids[i:i + _BATCH_SIZE]
                batch_vecs = embeddings[i:i + _BATCH_SIZE]
                batch_texts = texts[i:i + _BATCH_SIZE]
                batch_metas = metas[i:i + _BATCH_SIZE]

                points = [
                    qm.PointStruct(
                        id=did,
                        vector=vec,
                        payload={**meta, "text": text, "id": did},
                    )
                    for did, vec, text, meta in zip(batch_ids, batch_vecs, batch_texts, batch_metas)
                ]
                self._client.upsert(
                    collection_name=self.collection_name,
                    points=points,
                    wait=True,
                )
                written += len(points)

            return {
                "success": True,
                "added_count": written,
                "total_count": len(docs),
                "failed_count": len(docs) - len(valid),
            }
        except Exception as e:
            logger.error("add_documents_batch failed: %s", e)
            return {"success": False, "message": str(e)}

    # ------------------------------------------------------------------
    # Search — hybrid vector + keyword overlap
    # ------------------------------------------------------------------

    def search(self, query: str, k: int = 5, owner: Optional[str] = None) -> List[Dict[str, Any]]:
        if not self.healthy:
            return []
        if not query or not isinstance(query, str):
            return []
        total = _count(self._client, self.collection_name, owner=owner)
        if total == 0:
            return []

        try:
            fetch_k = min(max(k * 3, 20), total)
            if owner:
                fetch_k = min(fetch_k * 2, total)

            query_embeddings = self._embed([query])
            query_input = query_embeddings[0]

            qm = _qdrant_models()
            query_filter = _owner_filter(owner)

            if hasattr(self._client, "query_points"):
                response = self._client.query_points(
                    collection_name=self.collection_name,
                    query=query_input,
                    using=None,
                    query_filter=query_filter,
                    limit=fetch_k,
                    with_payload=True,
                )
                hits = response.points
            else:  # qdrant-client < 1.10
                hits = self._client.search(
                    collection_name=self.collection_name,
                    query_vector=query_input,
                    query_filter=query_filter,
                    limit=fetch_k,
                    with_payload=True,
                )

            query_words = set(query.lower().split())
            candidates: List[Dict[str, Any]] = []

            for hit in hits:
                payload = hit.payload or {}
                doc_text = payload.get("text", "")
                meta = {k: v for k, v in payload.items() if k != "text"}

                # Qdrant cosine returns similarity directly (higher = better).
                vector_sim = float(hit.score)

                doc_words = set(doc_text.lower().split())
                overlap = len(query_words & doc_words)
                keyword_score = overlap / len(query_words) if query_words else 0.0

                hybrid_score = (VECTOR_WEIGHT * vector_sim) + (KEYWORD_WEIGHT * keyword_score)

                candidates.append({
                    "id": payload.get("id", str(hit.id)),
                    "document": doc_text,
                    "metadata": meta,
                    "distance": round(1.0 - vector_sim, 4),  # back-compat with Chroma callers
                    "similarity": round(hybrid_score, 4),
                    "vector_similarity": round(vector_sim, 4),
                    "keyword_score": round(keyword_score, 4),
                })

            candidates.sort(key=lambda c: c["similarity"], reverse=True)
            top = candidates[:k]
            logger.info("Hybrid search for '%.60s': %d results", query, len(top))
            return top
        except Exception as e:
            logger.error("search failed: %s", e)
            return self._keyword_search_fallback(query, k, owner=owner)

    def _keyword_search_fallback(
        self, query: str, k: int = 5, owner: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        try:
            if _count(self._client, self.collection_name) == 0:
                return []

            qm = _qdrant_models()
            scroll_filter = _owner_filter(owner)
            seen: List[Dict[str, Any]] = []
            offset = None
            guard = 0
            query_words = query.lower().split()

            while True:
                guard += 1
                if guard > 1000:
                    break
                points, next_offset = self._client.scroll(
                    collection_name=self.collection_name,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                    scroll_filter=scroll_filter,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    doc = payload.get("text", "")
                    meta = {key: val for key, val in payload.items() if key != "text"}
                    doc_lower = doc.lower()
                    score = sum(1 for w in query_words if w in doc_lower)
                    if score > 0:
                        seen.append({
                            "id": payload.get("id", str(p.id)),
                            "document": doc,
                            "metadata": meta,
                            "distance": 0,
                            "similarity": float(score),
                            "search_type": "keyword_fallback",
                        })
                if next_offset is None:
                    break
                offset = next_offset

            seen.sort(key=lambda x: x["similarity"], reverse=True)
            return seen[:k]
        except Exception as e:
            logger.error("keyword fallback failed: %s", e)
            return []

    # ------------------------------------------------------------------
    # Index management
    # ------------------------------------------------------------------

    def rebuild_index(self) -> bool:
        try:
            from src.qdrant_client import get_qdrant_client
            client = get_qdrant_client()
            try:
                client.delete_collection(collection_name=self.collection_name)
            except Exception as e:
                status = getattr(e, "status_code", None)
                if status != 404 and "404" not in str(e):
                    raise
            if self._dim is None:
                # Shouldn't normally happen, but don't block rebuild if the
                # first init never landed — probe the embedding again.
                dims = self._model.encode(["dim probe"], normalize_embeddings=True)
                import numpy as np
                self._dim = int(np.asarray(dims).shape[-1])
            _ensure_collection(client, self.collection_name, self._dim)
            self._client = client
            self._healthy = True
            return True
        except Exception as e:
            logger.error("rebuild_index failed: %s", e)
            self._healthy = False
            return False

    def get_stats(self) -> Dict[str, Any]:
        if not self.healthy:
            return {"error": "VectorRAG not initialized"}
        try:
            count = _count(self._client, self.collection_name)
            return {
                "document_count": count,
                "embedding_model": f"{self._model.model} @ {self._model.url}" if self._model else "N/A",
                "persist_directory": self.persist_directory,
                "collection_name": self.collection_name,
                "backend": "qdrant",
                "healthy": True,
            }
        except Exception as e:
            logger.error("get_stats failed: %s", e)
            return {"error": str(e), "healthy": False}

    def delete_document(self, doc_id: str) -> bool:
        """Delete chunks whose source contains ``doc_id``.

        Historically Chroma used ``source`` as the canonical doc handle
        (``document:{id}``) and the source was matched with a substring
        filter. With Qdrant we scroll + exact-delete by id, preserving the
        contract.
        """
        if not self.healthy:
            logger.warning("Cannot delete document %s: RAG not healthy", doc_id)
            return False
        try:
            qm = _qdrant_models()
            deleted_ids: List[str] = []
            offset = None
            guard = 0
            while True:
                guard += 1
                if guard > 1000:
                    break
                points, next_offset = self._client.scroll(
                    collection_name=self.collection_name,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    source = payload.get("source", "")
                    if not source or doc_id not in source:
                        continue
                    deleted_ids.append(str(p.id))
                if next_offset is None:
                    break
                offset = next_offset

            if not deleted_ids:
                logger.debug("No chunks found for source pattern %s", doc_id)
                return False

            self._client.delete(
                collection_name=self.collection_name,
                points_selector=deleted_ids,
                wait=True,
            )
            logger.info("Deleted %d chunks for document %s", len(deleted_ids), doc_id)
            return True
        except Exception as e:
            logger.error("delete_document failed for %s: %s", doc_id, e)
            return False

    def delete_documents_by_source(self, source_prefix: str) -> int:
        """Delete chunks whose source starts with ``source_prefix``.

        Returns the deleted count (0 if no match).
        """
        if not self.healthy:
            logger.warning("Cannot delete with source `%s`: RAG not healthy", source_prefix)
            return 0
        try:
            deleted_ids: List[str] = []
            offset = None
            guard = 0
            while True:
                guard += 1
                if guard > 1000:
                    break
                points, next_offset = self._client.scroll(
                    collection_name=self.collection_name,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    source = payload.get("source", "")
                    if source and source.startswith(source_prefix):
                        deleted_ids.append(str(p.id))
                if next_offset is None:
                    break
                offset = next_offset

            if not deleted_ids:
                return 0

            self._client.delete(
                collection_name=self.collection_name,
                points_selector=deleted_ids,
                wait=True,
            )
            logger.info("Deleted %d chunks with source prefix %s", len(deleted_ids), source_prefix)
            return len(deleted_ids)
        except Exception as e:
            logger.error("delete_documents_by_source failed for %s: %s", source_prefix, e)
            return 0

    # ------------------------------------------------------------------
    # Directory indexing
    # ------------------------------------------------------------------

    def index_personal_documents(
        self, directory: str, file_extensions: Optional[set] = None, owner: Optional[str] = None
    ) -> Dict[str, Any]:
        if file_extensions is None:
            file_extensions = DEFAULT_FILE_EXTENSIONS

        indexed = 0
        failed = 0

        try:
            for root, _, files in os.walk(directory):
                for fname in files:
                    fpath = os.path.join(root, fname)
                    ext = Path(fname).suffix.lower()
                    if ext not in file_extensions:
                        continue

                    try:
                        if ext == '.pdf':
                            from src.personal_docs import extract_pdf_text
                            content = extract_pdf_text(fpath)
                        else:
                            with open(fpath, 'r', encoding='utf-8') as f:
                                content = f.read()

                        if not content or not content.strip():
                            continue

                        meta: Dict[str, Any] = {
                            'source': fpath,
                            'filename': fname,
                            'directory': root,
                            'type': ext,
                        }
                        if owner:
                            meta['owner'] = owner

                        for i, chunk in enumerate(self._split_into_chunks(content)):
                            if self.add_document(chunk, {**meta, 'chunk_id': i}):
                                indexed += 1
                            else:
                                failed += 1
                    except Exception as e:
                        logger.error("index %s: %s", fpath, e)
                        failed += 1

            return {
                'success': True,
                'indexed_count': indexed,
                'failed_count': failed,
                'message': f'Indexed {indexed} chunks from {directory}',
            }
        except Exception as e:
            logger.error("index_personal_documents %s: %s", directory, e)
            return {
                'success': False,
                'indexed_count': indexed,
                'failed_count': failed,
                'message': str(e),
            }

    def remove_directory(self, directory: str) -> Dict[str, Any]:
        """Delete every chunk whose source contains ``directory``."""
        if not self.healthy:
            return {"success": False, "message": "VectorRAG not initialized"}
        try:
            qm = _qdrant_models()
            # Match either by source-substring (parent path) or exact
            # directory field — preserves old Chroma semantics.
            scroll_filter = qm.Filter(
                should=[
                    qm.FieldCondition(key="source", match=qm.MatchText(text=directory)),
                    qm.FieldCondition(key="directory", match=qm.MatchValue(value=directory)),
                ]
            )

            deleted_ids: List[str] = []
            offset = None
            guard = 0
            while True:
                guard += 1
                if guard > 1000:
                    break
                points, next_offset = self._client.scroll(
                    collection_name=self.collection_name,
                    limit=256,
                    offset=offset,
                    with_payload=True,
                    with_vectors=False,
                    scroll_filter=scroll_filter,
                )
                if not points:
                    break
                for p in points:
                    payload = p.payload or {}
                    source = payload.get("source", "")
                    dir_field = payload.get("directory", "")
                    if (directory in source) or (dir_field == directory):
                        deleted_ids.append(str(p.id))
                if next_offset is None:
                    break
                offset = next_offset

            if not deleted_ids:
                return {"success": True, "removed_count": 0, "message": "No docs found"}

            # Qdrant's text-match does substring only on full-text fields so
            # we filtered the candidate list above by hand. Delete by id.
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=deleted_ids,
                wait=True,
            )
            logger.info("Removed %d chunks from %s", len(deleted_ids), directory)
            return {"success": True, "removed_count": len(deleted_ids), "message": f"Removed {len(deleted_ids)} chunks"}
        except Exception as e:
            logger.error("remove_directory %s: %s", directory, e)
            return {"success": False, "message": str(e)}

    def reindex_directory(
        self, directory: str, file_extensions: Optional[set] = None
    ) -> Dict[str, Any]:
        remove_result = self.remove_directory(directory)
        if not remove_result.get("success"):
            return remove_result
        index_result = self.index_personal_documents(directory, file_extensions)
        return {
            "success": index_result.get("success", False),
            "message": (
                f"Re-index for {directory}: removed {remove_result.get('removed_count', 0)}, "
                f"{index_result.get('message', '')}"
            ),
            "removed_count": remove_result.get("removed_count", 0),
            "indexed_count": index_result.get("indexed_count", 0),
            "failed_count": index_result.get("failed_count", 0),
        }

    # ------------------------------------------------------------------
    # Sentence-boundary-aware chunking (preserved verbatim from Chroma era)
    # ------------------------------------------------------------------

    def _split_into_chunks(
        self, text: str, chunk_size: int = 1000, overlap: int = 200
    ) -> List[str]:
        if not text:
            return []
        if len(text) <= chunk_size:
            return [text]

        sentences = re.split(r'(?<=[.!?])\s+|\n{2,}', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: List[str] = []
        current_chunk: List[str] = []
        current_len = 0

        for sentence in sentences:
            sent_len = len(sentence)

            if sent_len > chunk_size:
                if current_chunk:
                    chunks.append(' '.join(current_chunk))
                    current_chunk = []
                    current_len = 0

                for start in range(0, sent_len, chunk_size - overlap):
                    chunks.append(sentence[start:start + chunk_size])
                continue

            if current_len + sent_len + 1 > chunk_size and current_chunk:
                chunks.append(' '.join(current_chunk))
                overlap_sentences: List[str] = []
                overlap_len = 0
                for s in reversed(current_chunk):
                    if overlap_len + len(s) > overlap:
                        break
                    overlap_sentences.insert(0, s)
                    overlap_len += len(s) + 1
                current_chunk = overlap_sentences
                current_len = sum(len(s) for s in current_chunk) + max(0, len(current_chunk) - 1)

            current_chunk.append(sentence)
            current_len += sent_len + (1 if current_len > 0 else 0)

        if current_chunk:
            chunks.append(' '.join(current_chunk))

        return chunks if chunks else [text]

    # ------------------------------------------------------------------
    # Delete by metadata
    # ------------------------------------------------------------------

    def delete_by_source(self, source: str) -> int:
        """Remove all chunks whose ``source`` payload matches *source* exactly."""
        if not self.healthy:
            return 0
        try:
            qm = _qdrant_models()
            selector = qm.FilterSelector(filter=_source_filter(source))
            # ``count`` first to know how many we killed for the caller.
            before = _count(self._client, self.collection_name)
            self._client.delete(
                collection_name=self.collection_name,
                points_selector=selector,
                wait=True,
            )
            after = _count(self._client, self.collection_name)
            removed = max(0, before - after)
            logger.info("Deleted %d chunks for source=%s", removed, source)
            return removed
        except Exception as e:
            logger.error("delete_by_source failed: %s", e)
            return 0

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------

    def retrieve(self, query: str, k: int = 5) -> List[str]:
        return [r['document'] for r in self.search(query, k)]
