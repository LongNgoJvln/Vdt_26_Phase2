#!/usr/bin/env python3
"""Claim all ownerless data for a specific user.

Run once after enabling multi-user auth to assign existing data to the admin.

Usage:
    python scripts/claim_ownerless.py admin@example.com
"""

import sys
import os
import json
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/claim_ownerless.py <username>")
        sys.exit(1)

    owner = sys.argv[1]
    print(f"Claiming all ownerless data for: {owner}\n")

    # 1. Memories (JSON files)
    for label, path in [
        ("memory.json", "data/memory.json"),
        ("skills.json", "data/skills.json"),
    ]:
        if not os.path.exists(path):
            print(f"  {label}: not found, skipping")
            continue
        with open(path, "r", encoding="utf-8") as f:
            entries = json.load(f)
        count = 0
        for e in entries:
            if not e.get("owner"):
                e["owner"] = owner
                count += 1
        if count:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(entries, f, ensure_ascii=False, indent=2)
        print(f"  {label}: claimed {count} entries")

    # 2. Database tables (sessions, gallery, comparisons, documents)
    from core.database import SessionLocal, Session, Document
    try:
        from core.database import GalleryImage
    except ImportError:
        GalleryImage = None
    try:
        from core.database import Comparison
    except ImportError:
        Comparison = None

    db = SessionLocal()
    try:
        # Sessions
        count = db.query(Session).filter(Session.owner == None).update({"owner": owner})
        print(f"  sessions: claimed {count}")

        # Documents (have their own owner column; claim the ownerless ones,
        # mirroring the sessions/gallery/comparisons blocks). The old query set
        # session_id to itself — a no-op — and never set owner, so ownerless
        # documents stayed ownerless and invisible in the user's Library.
        count = db.query(Document).filter(Document.owner == None).update({"owner": owner})
        print(f"  documents: claimed {count}")

        # Gallery
        if GalleryImage:
            count = db.query(GalleryImage).filter(GalleryImage.owner == None).update({"owner": owner})
            print(f"  gallery: claimed {count}")

        # Comparisons
        if Comparison:
            count = db.query(Comparison).filter(Comparison.owner == None).update({"owner": owner})
            print(f"  comparisons: claimed {count}")

        db.commit()
    except Exception as e:
        db.rollback()
        print(f"  ERROR: {e}")
    finally:
        db.close()

    # 3. vault.json — under the vault_in_minio flag, BW_SESSION must move
    # out of the shared cross-tenant file into MinIO under userdata/<owner>/
    # as a Fernet-encrypted blob. Without this step, an operator flipping
    # the flag post-upgrade would see the admin locked out until the next
    # manual unlock (the per-owner bucket would be empty).
    vault_path = "data/vault.json"
    try:
        if os.path.exists(vault_path):
            with open(vault_path, "r", encoding="utf-8") as f:
                legacy_vault = json.load(f)
            if isinstance(legacy_vault, dict) and legacy_vault:
                from core import vault_store
                # ``save`` re-encrypts and uploads; failure must surface,
                # it raises RuntimeError. The legacy file is left as-is
                # so a re-run is safe.
                try:
                    vault_store.save(owner, legacy_vault)
                    print(f"  vault.json: uploaded encrypted to userdata/{owner}/vault.json.enc")
                except RuntimeError as exc:
                    print(f"  vault.json: FAILED to backfill: {exc}")
            else:
                print("  vault.json: empty / missing, nothing to backfill")
        else:
            print("  vault.json: not found, skipping")
    except Exception as exc:
        print(f"  vault.json: ERROR: {exc}")

    # 4. sessions.json — under the sessions_in_db flag, browser cookie
    # tokens move from the cross-tenant JSON blob into the auth_sessions
    # table. Without this step, an operator flipping the flag would lock
    # every active user out (the table would be empty; their cookies
    # would no longer validate). Each token row is owner-keyed by the
    # stored username, so claimant-style assignment isn't needed — every
    # live token just gets copied across. The source file is renamed
    # ``.bak`` afterward so a re-run is a no-op (rollback path: stop the
    # server, ``mv sessions.json.bak sessions.json``, drop the flag).
    sessions_path = "data/sessions.json"
    try:
        if os.path.exists(sessions_path):
            import time as _time
            from core import feature_flags as _ff
            from core.database import AuthSession as _AuthSess, SessionLocal as _SL
            from core import db_upsert as _du

            with open(sessions_path, "r", encoding="utf-8") as f:
                legacy = json.load(f)
            if isinstance(legacy, dict) and legacy:
                now = _time.time()
                live = [
                    (tok, meta.get("username", ""), int(meta.get("expiry", 0)))
                    for tok, meta in legacy.items()
                    if isinstance(meta, dict) and meta.get("expiry", 0) > now
                ]
                if live:
                    with _SL() as db:
                        _du.bulk_upsert(
                            db,
                            _AuthSess,
                            ["token"],
                            [
                                {
                                    "token": tok,
                                    "username": uname or owner,
                                    "expiry": exp,
                                    "created_at": datetime.utcnow(),
                                }
                                for tok, uname, exp in live
                            ],
                        )
                        db.commit()
                    # Add an audit marker; rename file to .bak only after
                    # commit landed. Failure between commit + rename is
                    # harmless — re-run sees no .json (rename was done).
                    os.rename(sessions_path, sessions_path + ".bak")
                    print(f"  sessions.json: backfilled {len(live)} token(s) → auth_sessions; old file → .bak")
                else:
                    os.rename(sessions_path, sessions_path + ".bak")
                    print("  sessions.json: no live tokens; old file → .bak")
            else:
                print("  sessions.json: empty / missing, nothing to backfill")
        else:
            print("  sessions.json: not found, skipping")
    except Exception as exc:
        print(f"  sessions.json: ERROR: {exc}")

    # 5. memory.json — under the memory_in_db flag, the canonical memory
    # store moves from the flat JSON file into the memories table. Without
    # this step, an operator flipping the flag would see every existing
    # memory "disappear" (load() returns []). Each row carries its own
    # owner, so ownerless entries first get attributed to ``owner`` above
    # (section 1), then every live row is bulk-upserted. The source file
    # is renamed ``.bak`` so a re-run is a no-op; rollback is
    # ``mv memory.json.bak memory.json`` + flip the flag back.
    memory_path = "data/memory.json"
    try:
        if os.path.exists(memory_path):
            from core.database import Memory as _Memory
            from core import db_upsert as _du
            from core.database import SessionLocal as _SL2

            with open(memory_path, "r", encoding="utf-8") as f:
                legacy_mem = json.load(f)
            if isinstance(legacy_mem, list) and legacy_mem:
                rows = []
                for e in legacy_mem:
                    if not isinstance(e, dict):
                        continue
                    rows.append({
                        "id": e.get("id") or f"mig-{os.urandom(8).hex()}",
                        "text": e.get("text", ""),
                        "category": e.get("category", "fact"),
                        "source": e.get("source", "user"),
                        "owner": e.get("owner") or owner,
                        "session_id": e.get("session_id"),
                        "timestamp": int(e.get("timestamp") or 0) or int(datetime.utcnow().timestamp()),
                    })
                if rows:
                    with _SL2() as db:
                        _du.bulk_upsert(db, _Memory, ["id"], rows)
                        db.commit()
                    os.rename(memory_path, memory_path + ".bak")
                    print(f"  memory.json: backfilled {len(rows)} entries → memories; old file → .bak")
                else:
                    os.rename(memory_path, memory_path + ".bak")
                    print("  memory.json: no usable entries; old file → .bak")
            else:
                print("  memory.json: empty / missing, nothing to backfill")
        else:
            print("  memory.json: not found, skipping")
    except Exception as exc:
        print(f"  memory.json: ERROR: {exc}")

    print(f"\nDone! All ownerless data now belongs to {owner}")
    print("Restart the server: sudo systemctl restart odysseus-ui")


if __name__ == "__main__":
    main()
