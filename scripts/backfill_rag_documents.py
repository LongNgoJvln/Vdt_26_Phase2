"""
One-shot backfill: ingest every library document that's missing from
the legacy RAG collection (``odysseus_rag``) into Qdrant.

Used after fixing ``_ingest_document_to_rag`` (chunking + owner scope +
non-silent errors) and after wiring ingest into the three document-creator
paths that were bypassing it. Existing rows that pre-date these fixes
never made it into the vector DB; this re-walks the ``documents`` table
and ingests any document by whose ``source`` tag is not already present
in the collection.

Run from project root::

    python -m scripts.backfill_rag_documents            # dry-run
    python -m scripts.backfill_rag_documents --apply     # actually ingest
    python -m scripts.backfill_rag_documents --apply --owner vht   # scope to one user

Success criterion: ``curl $QDRANT_URL/collections/odysseus_rag`` points_count
should increase by ~total_chunks_added after the run.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

# Make ``src/`` importable when run as a script.
_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

# Load .env before importing project modules so QDRANT_URL / embedding
# paths are set exactly as the running app sees them.
try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(dotenv_path=_ROOT / ".env", encoding="utf-8-sig")
except Exception as _e:
    logging.warning(f".env not loaded: {_e}")

from core.database import SessionLocal, Document  # noqa: E402
from routes.document_routes import _ingest_document_to_rag  # noqa: E402
from src.rag_singleton import get_rag_manager  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_rag")


def _list_existing_doc_sources(rag) -> set[str]:
    """Return the set of ``source`` payload values already in the collection.

    Used to skip documents whose points are already present (idempotent
    backfill) rather than re-embedding everything on every run.
    """
    from src.rag_vector import _qdrant_models  # noqa: F401

    client = getattr(rag, "client", None)
    collection = getattr(rag, "collection_name", None)
    if client is None or collection is None:
        return set()

    seen: set[str] = set()
    try:
        next_offset = None
        while True:
            res, next_offset = client.scroll(
                collection_name=collection,
                limit=256,
                offset=next_offset,
                with_payload=True,
                with_vectors=False,
            )
            for point in res:
                payload = point.payload or {}
                src = payload.get("source")
                if src:
                    seen.add(src)
            if next_offset is None:
                break
    except Exception as e:
        logger.warning(f"scroll failed; falling back to empty source set: {e}")
    return seen


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually ingest (default is dry-run)")
    ap.add_argument("--owner", default=None, help="Scope to a single owner (default: all)")
    args = ap.parse_args()

    rag = get_rag_manager()
    if not rag or not getattr(rag, "healthy", False):
        logger.error("RAG manager unavailable; aborting")
        return 1

    existing_sources = _list_existing_doc_sources(rag)
    logger.info(f"Collection already contains {len(existing_sources)} source tags")

    db = SessionLocal()
    try:
        q = db.query(Document).filter(Document.archived.is_(False))
        if args.owner:
            q = q.filter(Document.owner == args.owner)
        rows = q.all()
    finally:
        db.close()

    logger.info(f"Found {len(rows)} documents to consider (owner={args.owner or 'all'})")

    added = skipped_present = skipped_empty = failed = 0
    for doc in rows:
        src = f"document:{doc.id}"
        if src in existing_sources:
            skipped_present += 1
            continue
        if not (doc.current_content or "").strip():
            skipped_empty += 1
            continue
        if not args.apply:
            logger.info(f"[dry-run] would ingest doc id={doc.id} title={doc.title!r} owner={doc.owner}")
            added += 1
            continue
        try:
            _ingest_document_to_rag(doc)
            added += 1
        except Exception as e:
            failed += 1
            logger.warning(f"ingest failed for doc id={doc.id}: {e}")

    logger.info(
        f"Done: added={added} skipped_present={skipped_present} "
        f"skipped_empty={skipped_empty} failed={failed} "
        f"(apply={args.apply})"
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
