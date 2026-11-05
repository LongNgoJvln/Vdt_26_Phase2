"""Backfill ``data/scheduled_emails.db`` → Postgres bulk-upsert.

Idempotent: uses ``ON CONFLICT DO NOTHING``, so re-running the script
after a partial failure picks up where it left off.

Usage:
    DATABASE_URL=postgresql+psycopg://user:pass@host/odysseus \
    python scripts/migrate_scheduled_emails_to_pg.py [--sqlite data/scheduled_emails.db] [--batch 1000]

Old SQLite datetime strings (ISO / ``YYYY-MM-DD HH:MM:SS.ffffff``) are
parsed into tz-naive UTC datetimes — Postgres ``DateTime`` is tz-naive
by default so values round-trip cleanly.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import logging
import os
import pathlib
import sqlite3
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import Session as DBSession  # noqa: E402

from core import db_upsert  # noqa: E402
from core.database import (  # noqa: E402
    Base,
    EmailAiReply,
    EmailBoundary,
    EmailCalendarExtraction,
    EmailEventSeen,
    EmailSummary,
    EmailTag,
    EmailUrgencyAlert,
    ScheduledEmail,
    SenderSignature,
)

logger = logging.getLogger("migrate_scheduled_emails")

DEFAULT_SQLITE = pathlib.Path("data/scheduled_emails.db")

# Each entry: (sqlite_table, dest_model, conflict_cols, datetime_cols)
# Composite-PK tables (email_tags, email_event_seen)DECLARE their conflict
# columns explicitly; the others use the single PK column.
TABLE_PLAN = [
    ("scheduled_emails", ScheduledEmail, ["id"], ["send_at", "created_at", "updated_at"]),
    ("email_summaries", EmailSummary, ["message_id"], ["created_at"]),
    ("email_ai_replies", EmailAiReply, ["message_id"], ["created_at"]),
    ("email_tags", EmailTag, ["message_id", "owner"], ["created_at"]),
    ("email_calendar_extractions", EmailCalendarExtraction, ["message_id"], ["created_at"]),
    ("email_urgency_alerts", EmailUrgencyAlert, ["message_id"], ["created_at"]),
    ("email_boundaries", EmailBoundary, ["message_id"], ["created_at"]),
    ("sender_signatures", SenderSignature, ["from_address"], ["last_built_at"]),
    ("email_event_seen", EmailEventSeen, ["owner", "account_key", "folder", "message_key"], ["first_seen_at"]),
]

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
    # Fall through: best-effort fromisoformat (handles tz offsets too).
    try:
        return _dt.datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        logger.warning("unparseable datetime %r left as-is", raw)
        return None


def _fetch_sqlite_rows(sqlite_path: pathlib.Path, table: str, columns: list[str]):
    """Stream rows as dicts; closes the connection when done."""
    if not sqlite_path.exists():
        logger.warning("sqlite file %s missing — skipping %s", sqlite_path, table)
        return
    conn = sqlite3.connect(str(sqlite_path))
    conn.row_factory = sqlite3.Row
    try:
        cols_str = ", ".join(f'"{c}"' for c in columns)
        cur = conn.execute(f'SELECT {cols_str} FROM "{table}"')
        while True:
            batch = cur.fetchmany(1000)
            if not batch:
                break
            for row in batch:
                yield dict(row)
    finally:
        conn.close()


def _migrate_table(
    db: DBSession,
    sqlite_path: pathlib.Path,
    table: str,
    model,
    conflict_cols: list[str],
    dt_cols: list[str],
    batch_size: int,
    dry_run: bool,
) -> int:
    columns = [c.name for c in model.__table__.columns]
    batch: list[dict] = []
    written = 0

    def flush():
        nonlocal written
        if not batch:
            return
        if dry_run:
            written += len(batch)
            logger.info("[dry-run] would upsert %d rows into %s", len(batch), table)
        else:
            n = db_upsert.bulk_upsert(db, model, conflict_cols, list(batch))
            db.commit()
            written += n
            logger.info("upserted %d/%d rows into %s", n, len(batch), table)
        batch.clear()

    for row in _fetch_sqlite_rows(sqlite_path, table, columns):
        # Drop columns the destination model doesn't have (legacy cols).
        clean = {k: v for k, v in row.items() if k in columns}
        for dc in dt_cols:
            if dc in clean:
                clean[dc] = _parse_dt(clean[dc])
        # Skip rows missing required conflict-target values — would
        # violate constraint.
        if any(clean.get(c) is None for c in conflict_cols):
            continue
        batch.append(clean)
        if len(batch) >= batch_size:
            flush()
    flush()
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sqlite", default=str(DEFAULT_SQLITE), help="Path to scheduled_emails.db")
    parser.add_argument(
        "--pg-url",
        default=os.getenv("DATABASE_URL", ""),
        help="Target Postgres URL (defaults to env DATABASE_URL)",
    )
    parser.add_argument("--batch", type=int, default=1000)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--table",
        action="append",
        help="Restrict to one or more tables (repeatable). Defaults to all 9.",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    if "postgres" not in args.pg_url:
        logger.error("DATABASE_URL must point at Postgres; got %r", args.pg_url)
        return 2
    sqlite_path = pathlib.Path(args.sqlite)
    if not sqlite_path.exists():
        logger.error("sqlite file not found: %s", sqlite_path)
        return 2

    # Ensure target schema is at head first (idempotent).
    from alembic.config import Config
    from alembic import command

    logger.info("running alembic upgrade head on %s", args.pg_url)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")

    engine = create_engine(args.pg_url)
    total = 0
    with DBSession(engine) as db:
        for table, model, conflict_cols, dt_cols in TABLE_PLAN:
            if args.table and table not in args.table:
                continue
            n = _migrate_table(db, sqlite_path, table, model, conflict_cols, dt_cols, args.batch, args.dry_run)
            logger.info("table %s: %d rows migrated", table, n)
            total += n
    logger.info("done. total rows migrated: %d", total)
    return 0


if __name__ == "__main__":
    sys.exit(main())
