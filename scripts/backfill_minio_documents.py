"""
One-shot backfill: push every library document missing from per-user
object storage (MinIO/S3) into the bucket under ``userdata/{owner}/library/``.

Used after wiring ``_sync_document_to_minio`` into the document-creator
and document-update paths. Documents that pre-date those changes were
never copied to object storage; this re-walks the ``documents`` table
and uploads any row whose ``storage_path`` is empty or missing from the
bucket.

Run from project root::

    python -m scripts.backfill_minio_documents            # dry-run
    python -m scripts.backfill_minio_documents --apply     # actually upload
    python -m scripts.backfill_minio_documents --apply --owner vht   # one user

Success criterion: ``mc ls --recursive $ALIAS/$BUCKET/userdata/<owner>/library/``
should list one object per non-empty document.
"""
from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

try:
    from dotenv import load_dotenv  # noqa: E402
    load_dotenv(dotenv_path=_ROOT / ".env", encoding="utf-8-sig")
except Exception as _e:
    logging.warning(f".env not loaded: {_e}")

from core.database import SessionLocal, Document  # noqa: E402
from routes.document_routes import _sync_document_to_minio  # noqa: E402
from src.object_store import store  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_minio")


def _object_exists(owner: str, object_name: str) -> bool:
    """Return True iff ``userdata/{owner}/library/{object_name}`` exists."""
    if not getattr(store, "healthy", False):
        return False
    try:
        from src.object_store import _BUCKET
        full_key = f"userdata/{owner}/library/{object_name}"
        store._client.stat_object(_BUCKET, full_key)
        return True
    except Exception:
        return False


def _expected_object_name(doc) -> str:
    """Mirror the suffix logic in _sync_document_to_minio."""
    lang = (doc.language or "").lower()
    if lang == "email":
        return f"{doc.id}.eml"
    if lang in {"html", "xml"}:
        return f"{doc.id}.{lang}"
    if lang in {"python", "py"}:
        return f"{doc.id}.py"
    if lang in {"javascript", "js"}:
        return f"{doc.id}.js"
    if lang == "json":
        return f"{doc.id}.json"
    return str(doc.id)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="Actually upload (default is dry-run)")
    ap.add_argument("--owner", default=None, help="Scope to a single owner (default: all)")
    ap.add_argument(
        "--resync",
        action="store_true",
        help="Re-upload every document, even ones already in object storage",
    )
    args = ap.parse_args()

    if not getattr(store, "healthy", False):
        logger.error(
            "Object store not healthy (USE_MINIO=%s endpoint=%s); aborting",
            getattr(store, "_enabled", False), getattr(store, "_client", None),
        )
        return 1

    db = SessionLocal()
    try:
        q = db.query(Document).filter(Document.archived.is_(False))
        if args.owner:
            q = q.filter(Document.owner == args.owner)
        rows = q.all()
    finally:
        db.close()

    logger.info(
        "Found %d documents to consider (owner=%s resync=%s)",
        len(rows), args.owner or "all", args.resync,
    )

    uploaded = skipped_present = skipped_empty = failed = 0
    for doc in rows:
        if doc.owner is None:
            skipped_empty += 1
            continue
        if not (doc.current_content or "").strip():
            skipped_empty += 1
            continue
        if not args.resync:
            if doc.storage_path and _object_exists(doc.owner, _expected_object_name(doc)):
                skipped_present += 1
                continue
        if not args.apply:
            logger.info(
                "[dry-run] would upload doc id=%s title=%r owner=%s",
                doc.id, doc.title, doc.owner,
            )
            uploaded += 1
            continue
        try:
            _sync_document_to_minio(doc)
            uploaded += 1
        except Exception as e:
            failed += 1
            logger.warning(f"upload failed for doc id={doc.id}: {e}")

    logger.info(
        "Done: uploaded=%d skipped_present=%d skipped_empty=%d failed=%d (apply=%s)",
        uploaded, skipped_present, skipped_empty, failed, args.apply,
    )
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
