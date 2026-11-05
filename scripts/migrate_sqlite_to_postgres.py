#!/usr/bin/env python3
"""Copy every table from the legacy SQLite DB into a fresh Postgres target.

Usage:
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus \
        python scripts/migrate_sqlite_to_postgres.py \
        --sqlite ./data/app.db [--batch 1000] [--dry-run]

Idempotent: rows that fail FK or unique-constraint checks are logged
and skipped — the migration rolls nothing back. Re-running it after
fixing upstream issues picks up the missing rows.

This script does NOT modify the SQLite source. Run it in parallel with
the dual-write window so the Postgres side accumulates fresh writes too;
flip the read flag once row counts match.
"""
from __future__ import annotations

import argparse
import logging
import os
import sys
from datetime import datetime

# Project imports — operate against the same Base.metadata the app uses.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from core.database import Base, DATABASE_URL  # noqa: E402

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("sqlite_to_pg")


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--sqlite",
        default=os.getenv("SQLITE_PATH", "data/app.db"),
        help="Path to the legacy SQLite file (default: data/app.db)",
    )
    p.add_argument(
        "--pg-url",
        default=os.getenv("DATABASE_URL", DATABASE_URL),
        help="Target Postgres URL (default: $DATABASE_URL)",
    )
    p.add_argument("--batch", type=int, default=1000, help="Rows per batch")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Verify source row counts only; do not write to Postgres",
    )
    return p.parse_args()


def main() -> int:
    args = parse_args()

    if "postgresql" not in args.pg_url and "postgres" not in args.pg_url:
        log.error("--pg-url / $DATABASE_URL must point at Postgres, got %r", args.pg_url)
        return 2

    sqlite_url = f"sqlite:///{args.sqlite}"
    src = create_engine(sqlite_url)
    dst = create_engine(args.pg_url, pool_pre_ping=True, pool_size=5, max_overflow=5)

    log.info("source: %s", sqlite_url)
    log.info("target: %s", args.pg_url)

    # Ensure target schema is at head before copying rows.
    log.info("ensuring target schema is at alembic head …")
    from alembic.config import Config
    from alembic import command

    command.upgrade(Config("alembic.ini"), "head")

    if args.dry_run:
        log.info("dry-run: counting source rows only")
        with src.connect() as conn:
            for table in Base.metadata.sorted_tables:
                cnt = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table.name}").scalar()
                log.info("  %-30s %d rows", table.name, cnt)
        return 0

    total_in = 0
    total_out = 0
    started = datetime.utcnow()

    # sorted_tables gives FK-respecting topological order, so parent rows
    # land before children. Each batch is committed independently so a
    # mid-run crash leaves the schema and previously-committed batches intact.
    with dst.connect() as dst_conn:
        for table in Base.metadata.sorted_tables:
            with src.connect() as src_conn:
                # Stream via server-side cursor semantics: SQLAlchemy's
                # yield_per batches the result set without loading every
                # row into memory at once.
                log.info("copying %-30s …", table.name)
                rows_in = 0
                rows_out = 0
                failures = 0
                stream = src_conn.execution_options(stream_results=True).execute(
                    table.select()
                )
                batch: list[dict] = []
                for row in stream.mappings():
                    batch.append(dict(row))
                    if len(batch) >= args.batch:
                        n_in, n_out, n_fail = _bulk_insert(dst_conn, table, batch)
                        dst_conn.commit()
                        rows_in += n_in
                        rows_out += n_out
                        failures += n_fail
                        batch.clear()
                if batch:
                    n_in, n_out, n_fail = _bulk_insert(dst_conn, table, batch)
                    dst_conn.commit()
                    rows_in += n_in
                    rows_out += n_out
                    failures += n_fail
                log.info(
                    "  %-30s in=%d out=%d fail=%d",
                    table.name,
                    rows_in,
                    rows_out,
                    failures,
                )
                total_in += rows_in
                total_out += rows_out

    log.info(
        "migration complete in %.1fs — rows read=%d written=%d",
        (datetime.utcnow() - started).total_seconds(),
        total_in,
        total_out,
    )
    return 0


def _bulk_insert(dst_conn, table, batch: list[dict]) -> tuple[int, int, int]:
    """Insert a batch; on any failure, retry row-by-row so partial inserts
    still land and the bad rows are logged distinctly."""
    rows_in = len(batch)
    try:
        dst_conn.execute(table.insert(), batch)
        return rows_in, rows_in, 0
    except Exception as exc:
        log.warning("batch insert into %s failed (%s); retrying row-by-row", table.name, exc)
        written = 0
        failures = 0
        for row in batch:
            try:
                dst_conn.execute(table.insert(), [row])
                written += 1
            except Exception as row_exc:
                failures += 1
                log.error(
                    "  failed row on %s: %s — pk=%s",
                    table.name,
                    row_exc,
                    {c.name: row.get(c.name) for c in table.primary_key},
                )
        return rows_in, written, failures


if __name__ == "__main__":
    sys.exit(main())
