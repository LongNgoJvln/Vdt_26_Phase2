"""Typed DAO for the scheduled-email + AI cache tables.

Replaces raw ``sqlite3.connect(SCHEDULED_DB)`` blocks across the email
subsystem. Dispatches under the hood:

* ``features.infra_enabled("scheduled_emails_in_db")`` → SQLAlchemy
  against the ORM models in ``core.database``.
* otherwise → the legacy raw SQLite path via ``sqlite3.connect``.

All functions take ``owner`` (string username, never None) so cross-
tenant leaks surface as a misuse at the call-site rather than data
corruption at the row level. The composite-PK tables (``email_tags``
and ``email_event_seen``) are owner-scoped at the schema level.
"""
from __future__ import annotations

import json
import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from core.time_utils import utcnow_naive
from pathlib import Path
from typing import Any, Iterable, Iterator

from core import feature_flags
from core.database import (
    EmailAiReply,
    EmailBoundary,
    EmailCalendarExtraction,
    EmailEventSeen,
    EmailSummary,
    EmailTag,
    EmailUrgencyAlert,
    ScheduledEmail,
    SenderSignature,
    SessionLocal,
)

logger = logging.getLogger(__name__)

# Legacy path — kept for the dual-write window. Import lazily to avoid
# circular import into ``routes.email_helpers``.
_LEGACY_DB_DEFAULT = Path("data/scheduled_emails.db")


def _legacy_db_path() -> Path:
    try:
        from routes.email_helpers import SCHEDULED_DB  # noqa: WPS433
        return Path(SCHEDULED_DB)
    except Exception:
        return _LEGACY_DB_DEFAULT


@contextmanager
def _legacy_conn() -> Iterator[sqlite3.Connection]:
    conn = sqlite3.connect(str(_legacy_db_path()))
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _pg_enabled() -> bool:
    return bool(feature_flags.features.infra_enabled("scheduled_emails_in_db"))


def _dual() -> bool:
    return bool(feature_flags.features.infra_enabled("scheduled_emails_dual_write"))


def _to_dict(row) -> dict[str, Any]:
    """Convert a SQLAlchemy ORM row to a JSON-friendly dict.

    SQLAlchemy ``DateTime`` columns come back as ``datetime``; legacy
    callers expect ISO-formatted strings, so we stringify datetimes
    deterministically.
    """
    if row is None:
        return None  # type: ignore[return-value]
    out: dict[str, Any] = {}
    for col in row.__table__.columns:
        v = getattr(row, col.name, None)
        if isinstance(v, datetime):
            v = v.isoformat()
        out[col.name] = v
    return out


# ---------------------------------------------------------------------------
# Scheduled emails (outbound)
# ---------------------------------------------------------------------------

def insert_scheduled_email(row: dict[str, Any]) -> str | None:
    """Insert a pending outbound email row. Returns its ``id``.

    ``row`` should include all caller-supplied fields; missing fields
    default to None/``""`` via the model. ``created_at`` defaults to
    UTC now.
    """
    if "created_at" not in row:
        row["created_at"] = utcnow_naive()
    row.setdefault("status", "pending")

    if _pg_enabled():
        with SessionLocal() as db:
            obj = ScheduledEmail(**row)
            db.add(obj)
            db.commit()
            return obj.id
    if _dual():
        _insert_scheduled_email_legacy(row)
    return _insert_scheduled_email_legacy(row)


def _insert_scheduled_email_legacy(row: dict[str, Any]) -> str | None:
    payload = {**row}
    for k, v in list(payload.items()):
        if isinstance(v, datetime):
            payload[k] = v.isoformat()
    payload.setdefault("attachments", "[]")
    payload.setdefault("status", "pending")
    payload.setdefault("owner", "")
    cols = ", ".join(f'"{c}"' for c in payload.keys())
    placeholders = ", ".join("?" * len(payload))
    with _legacy_conn() as conn:
        conn.execute(
            f"INSERT INTO scheduled_emails ({cols}) VALUES ({placeholders})",
            list(payload.values()),
        )
    return payload.get("id")


def list_pending_scheduled_emails(
    *,
    owner: str = "",
    statuses: tuple[str, ...] = ("pending", "failed"),
) -> list[dict[str, Any]]:
    """List scheduled emails for an owner filtered to ``statuses``."""
    if _pg_enabled():
        with SessionLocal() as db:
            q = db.query(ScheduledEmail).filter(
                ScheduledEmail.owner == (owner or "")
            ).filter(ScheduledEmail.status.in_(statuses))
            q = q.order_by(ScheduledEmail.send_at.asc())
            return [_to_dict(r) for r in q.all()]

    statuses_clause = ",".join("?" * len(statuses))
    with _legacy_conn() as conn:
        cur = conn.execute(
            f"SELECT id, to_addr, cc, subject, send_at, created_at, status, error "
            f"FROM scheduled_emails WHERE status IN ({statuses_clause}) AND owner = ? "
            f"ORDER BY send_at ASC",
            (*statuses, owner or ""),
        )
        return [
            {
                "id": r[0], "to": r[1], "cc": r[2], "subject": r[3],
                "send_at": r[4], "created_at": r[5], "status": r[6], "error": r[7],
            }
            for r in cur.fetchall()
        ]


def fetch_pending_due(*, now_iso: str | None = None, batch: int = 200) -> list[dict[str, Any]]:
    """Pending sends whose ``send_at`` is at-or-before now.

    The poller calls this every tick. ``now_iso`` is the comparison
    point (caller owns the timezone policy); pass None for SQLite to
    compare as string-formatted ISO.
    """
    cutoff = now_iso or utcnow_naive().isoformat()
    if _pg_enabled():
        # On PG we have proper DateTime columns; parse the cutoff.
        cutoff_dt = cutoff if isinstance(cutoff, datetime) else _parse_iso(cutoff)
        with SessionLocal() as db:
            q = (
                db.query(ScheduledEmail)
                .filter(ScheduledEmail.status == "pending")
                .filter(ScheduledEmail.send_at <= cutoff_dt)
                .order_by(ScheduledEmail.send_at.asc())
                .limit(batch)
            )
            return [_to_dict(r) for r in q.all()]
    with _legacy_conn() as conn:
        rows = conn.execute(
            "SELECT id, to_addr, cc, bcc, subject, body, in_reply_to, references_hdr, "
            "       attachments, send_at, created_at, status, error, owner, account_id, "
            "       vhtna_kind "
            "FROM scheduled_emails WHERE status='pending' AND send_at <= ? "
            "ORDER BY send_at ASC LIMIT ?",
            (cutoff, batch),
        ).fetchall()
        cols = [
            "id", "to_addr", "cc", "bcc", "subject", "body", "in_reply_to",
            "references_hdr", "attachments", "send_at", "created_at", "status",
            "error", "owner", "account_id", "vhtna_kind",
        ]
        return [dict(zip(cols, r)) for r in rows]


def update_scheduled_email_status(
    *,
    sid: str,
    status: str,
    error: str | None = None,
    owner: str | None = None,
) -> int:
    """Mark a scheduled email sent/failed. Returns affected row count."""
    if _pg_enabled():
        with SessionLocal() as db:
            q = db.query(ScheduledEmail).filter(ScheduledEmail.id == sid)
            if owner is not None:
                q = q.filter(ScheduledEmail.owner == owner)
            rows = q.all()
            for row in rows:
                row.status = status
                if error is not None:
                    row.error = error
            db.commit()
            return len(rows)
    with _legacy_conn() as conn:
        if owner is not None:
            cur = conn.execute(
                "UPDATE scheduled_emails SET status=?, error=? WHERE id=? AND owner=?",
                (status, error, sid, owner),
            )
        else:
            cur = conn.execute(
                "UPDATE scheduled_emails SET status=?, error=? WHERE id=?",
                (status, error, sid),
            )
        return cur.rowcount or 0


def delete_scheduled_email(*, sid: str, owner: str) -> int:
    """Cancel a pending scheduled email. Idempotent."""
    if _pg_enabled():
        with SessionLocal() as db:
            rows = (
                db.query(ScheduledEmail)
                .filter(ScheduledEmail.id == sid)
                .filter(ScheduledEmail.owner == (owner or ""))
                .filter(ScheduledEmail.status == "pending")
                .delete(synchronize_session=False)
            )
            db.commit()
            return int(rows or 0)
    with _legacy_conn() as conn:
        cur = conn.execute(
            "DELETE FROM scheduled_emails WHERE id=? AND status='pending' AND owner=?",
            (sid, owner or ""),
        )
        return cur.rowcount or 0


# ---------------------------------------------------------------------------
# Event-seen deduplication table
# ---------------------------------------------------------------------------

def filter_unseen_message_keys(
    *,
    owner: str,
    account_key: str,
    folder: str,
    keys: list[str],
) -> list[str]:
    """Return the subset of ``keys`` not yet recorded as seen.

    Records every key as a side-effect (insert-if-not-exists). The
    legacy path uses ``INSERT OR IGNORE``; the PG path uses
    ``ON CONFLICT DO NOTHING``.
    """
    keys = [k for k in dict.fromkeys(keys) if k]
    if not keys:
        return []
    now = utcnow_naive()

    if _pg_enabled():
        from core import db_upsert
        with SessionLocal() as db:
            existing = {
                r.message_key
                for r in (
                    db.query(EmailEventSeen.message_key)
                    .filter(EmailEventSeen.owner == (owner or ""))
                    .filter(EmailEventSeen.account_key == account_key)
                    .filter(EmailEventSeen.folder == folder)
                    .filter(EmailEventSeen.message_key.in_(keys))
                    .all()
                )
            }
            new_rows = [
                {
                    "owner": owner or "",
                    "account_key": account_key,
                    "folder": folder,
                    "message_key": k,
                    "first_seen_at": now,
                }
                for k in keys
            ]
            db_upsert.bulk_upsert(
                db,
                EmailEventSeen,
                ["owner", "account_key", "folder", "message_key"],
                new_rows,
            )
            db.commit()
            return [k for k in keys if k not in existing]

    placeholders = ",".join("?" * len(keys))
    now_iso = now.isoformat()
    with _legacy_conn() as conn:
        cur = conn.execute(
            f"SELECT message_key FROM email_event_seen "
            f"WHERE owner=? AND account_key=? AND folder=? AND message_key IN ({placeholders})",
            (owner or "", account_key, folder, *keys),
        )
        existing = {r[0] for r in cur.fetchall()}
        conn.executemany(
            "INSERT OR IGNORE INTO email_event_seen "
            "(owner, account_key, folder, message_key, first_seen_at) VALUES (?, ?, ?, ?, ?)",
            [(owner or "", account_key, folder, k, now_iso) for k in keys],
        )
        return [k for k in keys if k not in existing]


# ---------------------------------------------------------------------------
# Tags + spam verdicts (composite PK: message_id + owner)
# ---------------------------------------------------------------------------

def _email_tag_owner_clause(account_id: str | None, owner: str | None) -> tuple[str, list[str]]:
    """Compatibility shim for ``_email_tag_owner_clause`` in email_routes.

    Returns (SQL fragment, binds) for the legacy path. The PG path
    ignores this and uses ORM filters directly.
    """
    if not owner:
        return ("owner = ''", [])
    return (
        "(owner = ? OR owner = '' OR owner = ?)",
        [owner, account_id or ""],
    )


def list_email_tags_where(
    *,
    folder: str | None = None,
    owner: str | None = None,
    account_id: str | None = None,
    spam_verdict: int | None = None,
) -> list[dict[str, Any]]:
    """Read tag rows filtered by folder/owner/spam_verdict.

    Each row includes ``message_id``, ``uid``, ``tags`` (raw JSON
    string — caller is responsible for parsing).
    """
    if _pg_enabled():
        with SessionLocal() as db:
            q = db.query(EmailTag)
            if folder is not None:
                q = q.filter(EmailTag.folder == folder)
            if owner:
                # Owner OR legacy null-owner rows OR account_id-aliased rows
                q = q.filter(
                    (EmailTag.owner == owner)
                    | (EmailTag.owner == "")
                    | (EmailTag.owner == (account_id or ""))
                )
            else:
                q = q.filter(EmailTag.owner == "")
            if spam_verdict is not None:
                q = q.filter(EmailTag.spam_verdict == spam_verdict)
            return [
                {
                    "message_id": r.message_id,
                    "uid": r.uid,
                    "tags": r.tags,
                    "spam_verdict": r.spam_verdict or 0,
                    "spam_reason": r.spam_reason,
                    "folder": r.folder,
                    "owner": r.owner,
                }
                for r in q.all()
            ]

    fragment, binds = _email_tag_owner_clause(account_id, owner)
    sql = (
        "SELECT message_id, uid, tags, spam_verdict, spam_reason "
        "FROM email_tags WHERE folder=? "
        f"AND {fragment}"
    )
    params: list[Any] = [folder, *binds]
    if spam_verdict is not None:
        sql += " AND spam_verdict=?"
        params.append(spam_verdict)
    with _legacy_conn() as conn:
        rows = conn.execute(sql, params).fetchall()
    return [
        {
            "message_id": r[0], "uid": r[1], "tags": r[2],
            "spam_verdict": r[3] or 0, "spam_reason": r[4], "folder": folder, "owner": owner,
        }
        for r in rows
    ]


def upsert_email_tag(row: dict[str, Any]) -> None:
    """Insert-or-update a tag row keyed by ``(message_id, owner)``."""
    if "created_at" not in row:
        row["created_at"] = utcnow_naive()
    if _pg_enabled():
        from core import db_upsert
        with SessionLocal() as db:
            db_upsert.upsert(
                db,
                EmailTag,
                ["message_id", "owner"],
                row,
                update_columns=[
                    c for c in row
                    if c not in ("message_id", "owner")
                ],
            )
            db.commit()
            return
    cols = list(row.keys())
    placeholders = ", ".join("?" * len(cols))
    update_cols = [c for c in cols if c not in ("message_id", "owner")]
    update_clause = ", ".join(f"{c}=excluded.{c}" for c in update_cols) if update_cols else "owner=excluded.owner"
    cols_str = ", ".join(cols)
    with _legacy_conn() as conn:
        conn.execute(
            f"INSERT INTO email_tags ({cols_str}) VALUES ({placeholders}) "
            f"ON CONFLICT(message_id, owner) DO UPDATE SET {update_clause}",
            [row[c] for c in cols],
        )


def clear_tables(
    tables: Iterable[str],
    *,
    owner: str | None = None,
) -> dict[str, int]:
    """``DELETE FROM`` each table. Returns ``{table_name: rows_removed}``.

    For ``email_tags`` and any owner-bearing table, when ``owner`` is
    truthy we delete rows where ``owner IN (owner, '')`` so legacy
    null-owner rows are swept along with the user's own.
    """
    if _pg_enabled():
        from sqlalchemy import delete as sa_delete
        result: dict[str, int] = {}
        with SessionLocal() as db:
            for table_name in tables:
                model = _MODEL_BY_TABLE.get(table_name)
                if model is None:
                    continue
                stmt = sa_delete(model)
                if owner and hasattr(model, "owner"):
                    stmt = stmt.where(model.owner.in_([owner, ""]))
                result[table_name] = db.execute(stmt).rowcount or 0
            db.commit()
        return result

    out: dict[str, int] = {}
    with _legacy_conn() as conn:
        for table_name in tables:
            try:
                if owner and table_name == "email_tags":
                    before = conn.execute(
                        "SELECT COUNT(*) FROM email_tags WHERE owner = ? OR owner = ''",
                        (owner,),
                    ).fetchone()[0]
                    conn.execute(
                        "DELETE FROM email_tags WHERE owner = ? OR owner = ''",
                        (owner,),
                    )
                else:
                    before = conn.execute(
                        f"SELECT COUNT(*) FROM {table_name}"
                    ).fetchone()[0]
                    conn.execute(f"DELETE FROM {table_name}")
                out[table_name] = int(before or 0)
            except sqlite3.OperationalError:
                out[table_name] = 0
    return out


_MODEL_BY_TABLE = {
    "scheduled_emails": ScheduledEmail,
    "email_summaries": EmailSummary,
    "email_ai_replies": EmailAiReply,
    "email_tags": EmailTag,
    "email_calendar_extractions": EmailCalendarExtraction,
    "email_urgency_alerts": EmailUrgencyAlert,
    "email_boundaries": EmailBoundary,
    "sender_signatures": SenderSignature,
    "email_event_seen": EmailEventSeen,
}


# ---------------------------------------------------------------------------
# Generic upserts — the poller + actions use these for the whitelist of
# tables where the existing schema is one-PK and the row content is
# shaped by the caller.
# ---------------------------------------------------------------------------

def upsert_by_pk(
    table_name: str,
    row: dict[str, Any],
    conflict_cols: list[str],
    *,
    update_cols: list[str] | None = None,
) -> int:
    """Insert-or-update a row by PK. Returns affected count."""
    model = _MODEL_BY_TABLE.get(table_name)
    if model is None:
        raise ValueError(f"unknown scheduled-email table: {table_name}")
    if _pg_enabled():
        from core import db_upsert
        with SessionLocal() as db:
            db_upsert.upsert(db, model, conflict_cols, row, update_cols)
            db.commit()
        return 1
    # sqlite ON CONFLICT
    cols = list(row.keys())
    placeholders = ", ".join("?" * len(cols))
    update_cols_eff = update_cols or [c for c in cols if c not in conflict_cols]
    update_clause = (
        ", ".join(f'"{c}"=excluded."{c}"' for c in update_cols_eff)
        if update_cols_eff
        else f'"{conflict_cols[0]}"=excluded."{conflict_cols[0]}"'
    )
    cols_quoted = ", ".join(f'"{c}"' for c in cols)
    conflict_quoted = ", ".join(f'"{c}"' for c in conflict_cols)
    with _legacy_conn() as conn:
        conn.execute(
            f'INSERT INTO "{table_name}" ({cols_quoted}) VALUES ({placeholders}) '
            f"ON CONFLICT({conflict_quoted}) DO UPDATE SET {update_clause}",
            [row[c] for c in cols],
        )
    return 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_iso(s: str) -> datetime:
    try:
        return datetime.fromisoformat(s.replace("Z", ""))
    except ValueError:
        try:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S.%f")
        except ValueError:
            return datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
