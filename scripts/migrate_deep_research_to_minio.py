#!/usr/bin/env python3
"""Backfill legacy ``data/deep_research/<id>.json`` into the per-owner store.

Run once after enabling ``ODYSSEUS_RESEARCH_IN_MINIO=true``. Each legacy row
already carries an ``owner`` field (stamped since D.5), so the script copies
each row into ``userdata/<owner>/research/<id>.json`` via the dual-write path
— the legacy flat file stays in place, which is what makes this safe to
re-run and easy to roll back (just flip the flag off).

Ownerless rows (pre-D.5 exports without an ``owner`` field) are attributed
to the ``--default-owner`` argument, which the operator should set to the
admin username. Without that attribution those rows would become invisible
under auth the moment the flag is flipped.

Usage:
    python scripts/migrate_deep_research_to_minio.py --default-owner admin@example.com
    python scripts/migrate_deep_research_to_minio.py --default-owner admin@example.com --dry-run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

LEGACY_DIR = Path("data/deep_research")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--default-owner",
        required=True,
        help="Username to attribute ownerless legacy rows to (typically the admin).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report what would happen without writing anything.",
    )
    args = parser.parse_args()

    from services.research import research_store

    if not LEGACY_DIR.exists():
        print(f"{LEGACY_DIR}: not found, nothing to backfill")
        return 0

    claimed = 0
    ownerless = 0
    failed = 0

    for p in sorted(LEGACY_DIR.glob("*.json")):
        rid = p.stem
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except Exception as exc:
            failed += 1
            print(f"  {rid}: FAILED to read ({exc})")
            continue

        if not isinstance(data, dict):
            failed += 1
            print(f"  {rid}: not a JSON object, skipping")
            continue

        row_owner = data.get("owner") or args.default_owner
        if not data.get("owner"):
            ownerless += 1
            data["owner"] = row_owner

        if args.dry_run:
            print(f"  {rid}: would save under userdata/{row_owner}/research/{rid}.json (dual-write)")
            claimed += 1
            continue

        try:
            research_store.save(row_owner, rid, data, dual_write=True)
            claimed += 1
        except Exception as exc:
            failed += 1
            print(f"  {rid}: FAILED to save ({exc})")

    print(
        f"\nBackfill complete: {claimed} promoted, "
        f"{ownerless} ownerless attributed to '{args.default_owner}', "
        f"{failed} failed."
    )
    if args.dry_run:
        print("Dry run only — no changes written.")
    else:
        print(
            "Legacy flat files preserved. Remove data/deep_research/ manually "
            "after the dual-write audit window."
        )
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
