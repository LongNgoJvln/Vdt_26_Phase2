"""Backfill ``<upload_dir>/uploads.json`` → Postgres ``uploads`` table.

Reads the flat JSON index that ``UploadHandler`` maintained under
``UPLOAD_DIR/uploads.json`` and bulk-inserts each entry into the
``Upload`` table behind ``ON CONFLICT DO NOTHING`` — idempotent across
re-runs so a partial failure picks up where it left off.

Usage:
    DATABASE_URL=postgresql+psycopg://user:pass@host/5432/odysseus \
        python scripts/migrate_uploads_to_pg.py [--json data/uploads/uploads.json] [--batch 500]

Legacy entries with no ``owner`` land as ``owner=NULL``; the composite
unique constraint ``(owner, sha256)`` treats NULLs as distinct per the
SQL standard, so legacy dupes do not collide.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import insert as pg_insert  # noqa: E402
from sqlalchemy.orm import Session as DBSession  # noqa: E402

from core.database import Base, Upload  # noqa: E402

logger = logging.getLogger("migrate_uploads")

DEFAULT_JSON = pathlib.Path("data/uploads/uploads.json")

# JSON keys → ORM column names. The legacy index carried a few aliases
# (``path`` / ``storage_path`` / ``name`` / ``hash``) used by callers;
# normalize them into the typed columns here.
KEY_MAP = {
    "id": "id",
    "file_scope": "file_scope",
    "session_id": "session_id",
    "original_name": "original_name",
    "safe_filename": "safe_filename",
    "mime": "mime",
    "size": "size",
    "sha256": "sha256",
    "client_ip": "client_ip",
    "uploaded_at": "uploaded_at",
    "last_accessed": "last_accessed",
    "expires_at": "expires_at",
    "minio_key": "minio_key",
    "local_path": "local_path",
    "width": "width",
    "height": "height",
    "owner": "owner",
}

DATETIME_KEYS = ("uploaded_at", "last_accessed", "expires_at", "created_at", "updated_at")

DT_FORMATS = (
    "%Y-%m-%d %H:%M:%S.%f",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%dT%H:%M:%S.%f",
    "%Y-%m-%dT%H:%M:%S",
)


def _parse_dt(raw):
    if raw is None or raw == "":
        return None
    if isinstance(raw, _dt.datetime):
        return raw
    s = str(raw).strip()
    if not s:
        return None
    for fmt in DT_FORMATS:
        try:
            return _dt.datetime.strptime(s, fmt)
        except ValueError:
            continue
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        logger.warning("unparseable datetime %r left as None", raw)
        return None


def _normalize_entry(raw: dict) -> dict | None:
    """Translate a legacy JSON entry to an Upload-row dict.

    Returns None for entries missing the required ``id`` or ``sha256`` —
    a junk row in the JSON file shouldn't abort the whole backfill.
    """
    if not isinstance(raw, dict):
        return None
    # Pull the canonical names first; fall back to legacy aliases when the
    # JSON entry was written by an older code path.
    safe_filename = raw.get("safe_filename") or raw.get("name")
    sha256 = raw.get("sha256") or raw.get("hash")
    local_path = raw.get("local_path") or raw.get("path")
    minio_key = raw.get("minio_key") or raw.get("storage_path")
    original_name = raw.get("original_name") or safe_filename

    out: dict = {}
    for src_key, dst_col in KEY_MAP.items():
        if src_key in raw:
            out[dst_col] = raw[src_key]

    # Apply alias fallbacks computed above.
    if safe_filename is not None:
        out["safe_filename"] = safe_filename
    if sha256 is not None:
        out["sha256"] = sha256
    if local_path is not None:
        out["local_path"] = local_path
    if minio_key is not None:
        out["minio_key"] = minio_key
    if original_name is not None:
        out["original_name"] = original_name

    # Apply hardcoded defaults the model would have set itself for new rows.
    out.setdefault("file_scope", "library")

    # Parse datetimes so they land in DateTime columns, not TEXT.
    for k in DATETIME_KEYS:
        if k in out:
            out[k] = _parse_dt(out[k])

    now = _dt.datetime.utcnow()
    out.setdefault("uploaded_at", now)
    out.setdefault("last_accessed", out["uploaded_at"] or now)
    out.setdefault("created_at", now)
    out.setdefault("updated_at", now)

    # Drop empty strings on required NOT NULL fields — would fail INSERT.
    for req in ("id", "safe_filename", "original_name", "mime"):
        if out.get(req) in (None, ""):
            if req == "mime":
                out[req] = "application/octet-stream"
            elif req in ("safe_filename", "original_name"):
                out[req] = out.get("id") or "unknown"
            else:
                return None
    if out.get("size") is None:
        out["size"] = 0
    if out.get("sha256") in (None, ""):
        return None

    return out


def _load_json(path: pathlib.Path) -> list[dict]:
    if not path.exists():
        logger.error("uploads JSON not found: %s", path)
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("failed to read %s: %s", path, exc)
        return []
    # Two on-disk shapes have existed: a flat dict ``{id: entry}`` (the
    # current format) and a list of entries (older deploys).
    if isinstance(data, dict):
        return list(data.values())
    if isinstance(data, list):
        return data
    logger.error("unexpected JSON shape in %s (got %s)", path, type(data).__name__)
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="Path to uploads.json")
    parser.add_argument(
        "--pg-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Target Postgres URL (defaults to env DATABASE_URL)",
    )
    parser.add_argument("--batch", type=int, default=500)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "postgres" not in args.pg_url:
        logger.error("DATABASE_URL must point at Postgres; got %r", args.pg_url)
        return 2

    json_path = pathlib.Path(args.json)
    if not json_path.exists():
        logger.error("uploads JSON file not found: %s", json_path)
        return 2

    # Ensure target schema is at head first (idempotent).
    from alembic.config import Config
    from alembic import command

    logger.info("running alembic upgrade head on %s", args.pg_url)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")

    raw_entries = _load_json(json_path)
    logger.info("loaded %d raw entries from %s", len(raw_entries), json_path)

    rows: list[dict] = []
    skipped = 0
    for raw in raw_entries:
        norm = _normalize_entry(raw)
        if norm is None:
            skipped += 1
            continue
        rows.append(norm)
    logger.info("normalized %d rows (%d skipped)", len(rows), skipped)

    if args.dry_run:
        logger.info("[dry-run] would insert %d rows into uploads", len(rows))
        return 0

    engine = create_engine(args.pg_url)
    written = 0
    with DBSession(engine) as db:
        for i in range(0, len(rows), args.batch):
            batch = rows[i : i + args.batch]
            # ON CONFLICT DO NOTHING without an index_elements — any
            # constraint violation (PK or the (owner, sha256) unique
            # constraint) silently skips the row. Safe for re-runs.
            stmt = pg_insert(Upload).values(batch).on_conflict_do_nothing()
            result = db.execute(stmt)
            written += result.rowcount or 0
        db.commit()
    logger.info("done. rows inserted: %d (skipped duplicates: %d)", written, len(rows) - written)
    return 0


if __name__ == "__main__":
    sys.exit(main())
