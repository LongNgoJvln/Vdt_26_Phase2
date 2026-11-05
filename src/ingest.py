"""
ingest.py

Async pipeline that turns an uploaded file into RAG chunks.

`POST /api/upload` lands bytes in MinIO + writes an `Upload` DB row; it never
touches the vector index. `ingest_upload_to_rag` is the missing second half:
read the bytes back from local FS or MinIO, crack the file format into text,
chunk, embed, and write into the caller's per-owner VectorRAG collection.

Designed for fire-and-forget — `POST /api/upload` schedules this via
``asyncio.create_task`` and returns immediately. Status is tracked in an
in-memory dict keyed by upload_id so the UI can poll
`GET /api/upload/{file_id}/ingest-status` for completion.
"""

from __future__ import annotations

import logging
import os
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Ingestion is bounded to these extensions. Extensions outside this set
# return ``status="skipped"`` (e.g. images, video, audio — vector RAG has
# nothing to do with them).
_INGESTIBLE_EXTS = frozenset({
    ".txt", ".md", ".markdown", ".csv", ".json", ".yaml", ".yml",
    ".html", ".htm",
    ".py", ".js", ".ts", ".tsx", ".jsx", ".css", ".java", ".go",
    ".rs", ".c", ".cpp", ".h", ".hpp", ".sh", ".rb", ".php", ".sql",
    ".xml", ".log",
    ".pdf",
    ".docx", ".pptx", ".xlsx", ".xls", ".epub",
})


@dataclass
class IngestResult:
    """Outcome of a single ingest_upload_to_rag call."""

    status: str  # "ok" | "failed" | "skipped"
    chunks: int = 0
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {"status": self.status, "chunks": self.chunks, "error": self.error}


@dataclass
class _IngestStateEntry:
    status: str  # "pending" | "ok" | "failed" | "skipped"
    chunks: int = 0
    error: Optional[str] = None
    updated_at: float = field(default_factory=time.time)


# Module-level state. defaultdict so callers don't have to pre-create keys.
# Terminal entries (ok/failed/skipped) are pruned after _TTL_SECONDS so the
# dict can't grow unboundedly across long-running workers.
_INGEST_STATE: Dict[str, "_IngestStateEntry"] = defaultdict(_IngestStateEntry.__new__)
_TTL_SECONDS = 3600


def _set_state(upload_id: str, status: str, *, chunks: int = 0, error: Optional[str] = None) -> None:
    _INGEST_STATE[upload_id] = _IngestStateEntry(
        status=status, chunks=chunks, error=error, updated_at=time.time()
    )
    _prune_state()


def get_ingest_status(upload_id: str) -> Optional[Dict[str, Any]]:
    entry = _INGEST_STATE.get(upload_id)
    if entry is None:
        return None
    return {"status": entry.status, "chunks": entry.chunks, "error": entry.error}


def _prune_state() -> None:
    now = time.time()
    stale = [
        uid for uid, e in _INGEST_STATE.items()
        if e.status in ("ok", "failed", "skipped") and now - e.updated_at > _TTL_SECONDS
    ]
    for uid in stale:
        _INGEST_STATE.pop(uid, None)


def _decode_text(raw: bytes) -> str:
    """Decode raw bytes to text, falling back to charset_normalizer on UTF-8 failure."""
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        try:
            from charset_normalizer import detect
            encoding = (detect(raw) or {}).get("encoding") or "utf-8"
            return raw.decode(encoding, errors="replace")
        except Exception:
            return raw.decode("utf-8", errors="replace")


def _strip_html(raw: bytes) -> str:
    """Strip tags from an HTML document. Falls back to a regex sweep if BS4 is missing."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(raw, "html.parser")
        return soup.get_text(separator="\n", strip=True)
    except ImportError:
        import re
        text = _decode_text(raw)
        text = re.sub(r"<script[^>]*>.*?</script>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        return text


def extract_text(path: str, ext: Optional[str] = None) -> str:
    """Extract plain text from a file on disk based on its extension.

    Returns "" when extraction is unavailable (e.g. markitdown missing or
    broken PDF). Callers should treat empty as "skip" rather than error.
    """
    if not path or not os.path.exists(path):
        return ""
    if ext is None:
        ext = os.path.splitext(path)[1].lower()

    if ext in (".pdf",):
        try:
            from src.personal_docs import extract_pdf_text
            return extract_pdf_text(path) or ""
        except Exception as e:
            logger.warning(f"ingest: PDF extraction failed for {path}: {e}")
            return ""

    if ext in (".docx", ".pptx", ".xlsx", ".xls", ".epub"):
        try:
            from src.personal_docs import extract_office_text
            return extract_office_text(path) or ""
        except Exception as e:
            logger.warning(f"ingest: office extraction failed for {path}: {e}")
            return ""

    if ext in (".html", ".htm"):
        try:
            with open(path, "rb") as f:
                return _strip_html(f.read())
        except Exception as e:
            logger.warning(f"ingest: HTML read failed for {path}: {e}")
            return ""

    # Plain text / code / data — read bytes and decode
    try:
        with open(path, "rb") as f:
            return _decode_text(f.read())
    except Exception as e:
        logger.warning(f"ingest: text read failed for {path}: {e}")
        return ""


def _resolve_local_path(
    upload_meta: Dict[str, Any], *, upload_handler=None
) -> Optional[str]:
    """Return a readable local path for the upload meta, fetching from MinIO if needed.

    Returns None when bytes cannot be made available locally. The caller
    treats that as a skipped ingest so the upload itself still succeeds.
    """
    path = upload_meta.get("path")
    if path and os.path.exists(path):
        return path

    # MinIO-only uploads require a fetch-back into the local cache.
    upload_id = upload_meta.get("id")
    owner = upload_meta.get("owner")
    if not upload_id or not owner or upload_handler is None:
        return None

    try:
        fetched = upload_handler.fetch_from_minio(upload_id, owner=owner)
        return fetched
    except Exception as e:
        logger.warning(f"ingest: fetch_from_minio failed for upload {upload_id}: {e}")
        return None


async def ingest_upload_to_rag(
    *,
    upload_meta: Dict[str, Any],
    owner: Optional[str],
    vector_rag,
    upload_handler=None,
) -> IngestResult:
    """Run ingestion for one upload, fire-and-forget style.

    Args:
        upload_meta: dict returned by ``upload_handler.save_upload`` — must
            include ``id``, ``name``, ``path`` (optional, may be MinIO-only),
            and either ``path`` or ``minio_key`` + ``owner`` so we can fetch
            bytes on cache miss.
        owner: username for per-tenant isolation. Always written into chunk
            metadata — empty string is legacy-only.
        vector_rag: VectorRAG instance from ``get_rag_manager()``. Caller
            lazy-resolves it so this function doesn't import rag_singleton.
        upload_handler: the UploadHandler for MinIO fetch-back on cache miss.
            Injected by the route factory — ingest.py deliberately has no
            handle on the global handler.

    Returns:
        IngestResult describing outcome. Also updates the in-memory state
        dict keyed by upload_meta["id"] so the status endpoint can poll.
    """
    upload_id = upload_meta.get("id") or ""
    if not upload_id:
        return IngestResult(status="failed", error="missing upload id")

    filename = upload_meta.get("name") or "upload"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in _INGESTIBLE_EXTS:
        logger.info(f"ingest: skipping non-text upload {filename} (ext={ext!r})")
        _set_state(upload_id, "skipped", error=f"unsupported extension: {ext}")
        return IngestResult(status="skipped")

    if vector_rag is None or not getattr(vector_rag, "healthy", False):
        logger.warning(f"ingest: vector_rag unavailable for upload {upload_id}")
        _set_state(upload_id, "failed", error="RAG vector store unavailable")
        return IngestResult(status="failed", error="RAG vector store unavailable")

    _set_state(upload_id, "pending")

    local_path = _resolve_local_path(upload_meta, upload_handler=upload_handler)
    if not local_path:
        _set_state(upload_id, "failed", error="could not resolve local file for ingest")
        return IngestResult(status="failed", error="could not resolve local file")

    try:
        text = extract_text(local_path, ext)
    except Exception as e:
        logger.error(f"ingest: extraction threw for upload {upload_id}: {e}")
        _set_state(upload_id, "failed", error=f"extraction error: {e}")
        return IngestResult(status="failed", error=f"extraction error: {e}")

    if not text or not text.strip():
        logger.info(f"ingest: no text extracted from {filename}; skipping")
        _set_state(upload_id, "skipped", error="no text content")
        return IngestResult(status="skipped")

    try:
        chunks = vector_rag._split_into_chunks(text)
    except Exception as e:
        logger.error(f"ingest: chunking failed for upload {upload_id}: {e}")
        _set_state(upload_id, "failed", error=f"chunking error: {e}")
        return IngestResult(status="failed", error=f"chunking error: {e}")

    if not chunks:
        _set_state(upload_id, "skipped", error="no chunks produced")
        return IngestResult(status="skipped")

    base_meta = {
        "owner": owner or "",
        "source": "upload",
        "upload_id": upload_id,
        "filename": filename,
        "type": ext,
    }

    added = 0
    last_error: Optional[str] = None
    for i, chunk in enumerate(chunks):
        meta = {**base_meta, "chunk_id": i}
        try:
            if vector_rag.add_document(chunk, meta):
                added += 1
        except Exception as e:
            last_error = str(e)
            logger.warning(f"ingest: add_document failed for chunk {i} of {upload_id}: {e}")

    if added == 0:
        status = "failed"
        error = last_error or "no chunks were added"
        _set_state(upload_id, status, error=error)
        return IngestResult(status=status, chunks=0, error=error)

    logger.info(
        "ingest: completed upload=%s owner=%s chunks_added=%s/%s ext=%s",
        upload_id, owner, added, len(chunks), ext,
    )
    _set_state(upload_id, "ok", chunks=added)
    return IngestResult(status="ok", chunks=added, error=last_error)
