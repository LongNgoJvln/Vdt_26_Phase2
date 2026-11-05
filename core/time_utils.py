"""Time utilities — the single home for "now" and datetime normalization.

Convention (see docs + CLAUDE.md):
- All datetimes in Python are timezone-aware UTC.
- Storage stays naive-UTC (WITHOUT TIME ZONE columns); ``UtcDateTime``
  normalizes at the ORM boundary so code sees aware values either way.
- API serialization is canonical ISO-8601 with a trailing ``Z``.

Python floor is 3.10 — do NOT use 3.11+ datetime APIs
(``fromisoformat("...Z")`` is 3.11+); use :func:`parse_iso`.
"""
from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utcnow() -> datetime:
    """Aware UTC now — the replacement for the deprecated ``datetime.utcnow()``."""
    return datetime.now(timezone.utc)


def utcnow_naive() -> datetime:
    """Naive UTC now.

    ONLY for legacy TEXT stores (scheduled_emails) and naive-by-design
    comparisons (calendar wall times, search ranking publish dates).
    """
    return utcnow().replace(tzinfo=None)


def as_utc(dt):
    """None-safe normalize: a naive value is assumed to be UTC and made aware."""
    if dt is None or (isinstance(dt, datetime) and dt.tzinfo is not None):
        return dt
    return dt.replace(tzinfo=timezone.utc)


def to_db(dt):
    """Aware -> naive UTC for raw-SQL writes into naive-UTC columns."""
    if dt is None or dt.tzinfo is None:
        return dt
    return dt.astimezone(timezone.utc).replace(tzinfo=None)


def parse_iso(s):
    """Parse an ISO string (3.10-safe with 'Z') and return aware UTC."""
    if isinstance(s, str) and s.endswith("Z"):
        s = s.replace("Z", "+00:00")
    return as_utc(datetime.fromisoformat(s))


def iso_utc(value):
    """THE canonical serializer for API output — always a trailing 'Z'.

    Accepts datetimes and ISO strings; falls back to ``str()`` for any other
    type so it can serve as a ``json.dumps(default=...)`` hook.
    """
    if value is None:
        return None
    if isinstance(value, datetime):
        return as_utc(value).isoformat().replace("+00:00", "Z")
    if isinstance(value, str):
        try:
            return parse_iso(value).isoformat().replace("+00:00", "Z")
        except ValueError:
            return value
    return str(value)


class UtcDateTime(TypeDecorator):
    """Naive-UTC storage, aware-UTC in Python.

    ``process_bind_param`` strips the zone before the driver sees the value
    (kills Postgres session-timezone coercion); ``process_result_value``
    re-attaches UTC on the way out (SQLite always reads back naive).
    """

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        return to_db(value)

    def process_result_value(self, value, dialect):
        return as_utc(value)
