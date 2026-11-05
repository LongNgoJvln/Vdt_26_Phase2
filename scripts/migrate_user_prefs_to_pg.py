"""Backfill ``data/user_prefs.json`` ``_users`` → Postgres ``user_settings``.

The legacy prefs file stored every user's overrides as
``{_users: {username: {key: value, ...}}}`` — one physical blob, full
rewrite on any per-key change. Each ``(username, key)`` pair becomes one
row in ``user_settings(owner, key, value_json)`` behind ``ON CONFLICT DO
NOTHING``, so re-runs pick up where a partial failure left off.

Usage:
    DATABASE_URL=postgresql+psycopg://user:pass@host:5432/odysseus \
        python scripts/migrate_user_prefs_to_pg.py [--json data/user_prefs.json] [--batch 500]
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

from core.database import UserSetting  # noqa: E402

logger = logging.getLogger("migrate_user_prefs")

DEFAULT_JSON = pathlib.Path("data/user_prefs.json")


def _load_users_block(path: pathlib.Path) -> dict:
    if not path.exists():
        logger.error("user_prefs JSON not found: %s", path)
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("failed to read %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.error("unexpected JSON shape in %s (got %s)", path, type(data).__name__)
        return {}
    users = data.get("_users")
    if users is None:
        # Pre-multi-user deploys stored a single flat prefs dict with no
        # ``_users`` wrapper. Nothing to backfill in that case.
        logger.info("no _users block in %s — nothing to backfill", path)
        return {}
    if not isinstance(users, dict):
        logger.error("_users block in %s is not a dict", path)
        return {}
    return users


def _flatten(users: dict) -> list[dict]:
    rows: list[dict] = []
    for owner, prefs in users.items():
        if not isinstance(owner, str) or not owner.strip():
            continue
        if not isinstance(prefs, dict):
            continue
        for key, value in prefs.items():
            if not isinstance(key, str) or not key:
                continue
            rows.append({
                "owner": owner,
                "key": key,
                "value_json": json.dumps(value),
                "created_at": _dt.datetime.utcnow(),
                "updated_at": _dt.datetime.utcnow(),
            })
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--json", default=str(DEFAULT_JSON), help="Path to user_prefs.json")
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
        logger.error("user_prefs JSON file not found: %s", json_path)
        return 2

    from alembic.config import Config
    from alembic import command

    logger.info("running alembic upgrade head on %s", args.pg_url)
    command.upgrade(Config(str(ROOT / "alembic.ini")), "head")

    users = _load_users_block(json_path)
    if not users:
        logger.info("no users to backfill; exiting")
        return 0
    logger.info("loaded %d users from %s", len(users), json_path)

    rows = _flatten(users)
    logger.info("flattened %d (owner, key) rows", len(rows))

    if args.dry_run:
        logger.info("[dry-run] would insert %d rows into user_settings", len(rows))
        return 0

    engine = create_engine(args.pg_url)
    written = 0
    with DBSession(engine) as db:
        for i in range(0, len(rows), args.batch):
            batch = rows[i : i + args.batch]
            stmt = (
                pg_insert(UserSetting)
                .values(batch)
                .on_conflict_do_nothing(index_elements=["owner", "key"])
            )
            result = db.execute(stmt)
            written += result.rowcount or 0
        db.commit()
    logger.info(
        "done. rows inserted: %d (skipped duplicates: %d)",
        written,
        len(rows) - written,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
