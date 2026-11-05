"""Upsert helper for PostgreSQL (and a SQLite-safe fallback).

Postgres has ``INSERT ... ON CONFLICT``; SQLite has ``INSERT OR REPLACE``
but the semantics on unchanged columns differ. This module hides both
behind one typed ``upsert()`` so callers don't have to branch on dialect.

The function takes a SQLAlchemy session, a model class, the conflict
target columns, and a values dict. On Postgres it uses
``sqlalchemy.dialects.postgresql.insert(...).on_conflict_do_update``;
on SQLite it falls back to a manual delete+insert inside the same
transaction so the behaviour matches.
"""
from __future__ import annotations

import logging
from typing import Any, Iterable, Type

from sqlalchemy import inspect
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError

logger = logging.getLogger(__name__)


def upsert(
    session: Session,
    model: Type,
    conflict_columns: Iterable[str],
    values: dict[str, Any],
    update_columns: Iterable[str] | None = None,
) -> Any:
    """Insert or update ``model`` keyed by ``conflict_columns``.

    On conflict, columns listed in ``update_columns`` are written from
    the new values; columns not listed are untouched. If
    ``update_columns`` is None, all columns in ``values`` other than the
    conflict columns are written (full replace).

    Returns the ORM instance bound to ``session`` after the upsert.
    """
    conflict_cols = list(conflict_columns)
    dialect_name = session.bind.dialect.name if session.bind else ""

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(model).values(**values)
        set_cols = (
            list(update_columns)
            if update_columns is not None
            else [c for c in values if c not in conflict_cols]
        )
        set_dict = {c: getattr(stmt.excluded, c) for c in set_cols}
        if set_dict:
            stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=set_dict)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
        session.execute(stmt)
        session.flush()
        # Re-read to attach the ORM instance.
        filt = [getattr(model, c) == values[c] for c in conflict_cols]
        return session.query(model).filter(*filt).first()

    # SQLite (and others): emulate with delete+insert inside the same txn.
    filt = [getattr(model, c) == values[c] for c in conflict_cols]
    existing = session.query(model).filter(*filt).first()
    if existing is not None:
        set_cols = (
            list(update_columns)
            if update_columns is not None
            else [c for c in values if c not in conflict_cols]
        )
        for col in set_cols:
            setattr(existing, col, values[col])
        session.flush()
        return existing

    # Map JSON-named columns back to ORM attribute names in case of alias.
    mapper = inspect(model)
    attr_values = {}
    for k, v in values.items():
        # Find an ORM attr that maps to this column name.
        attr_name = k
        for attr in mapper.column_attrs:
            if attr.columns[0].name == k:
                attr_name = attr.key
                break
        attr_values[attr_name] = v
    obj = model(**attr_values)
    session.add(obj)
    session.flush()
    return obj


def bulk_upsert(
    session: Session,
    model: Type,
    conflict_columns: Iterable[str],
    rows: list[dict[str, Any]],
    update_columns: Iterable[str] | None = None,
) -> int:
    """Bulk variant: applies upsert semantics for many rows.

    Returns the count of rows touched. Uses Postgres-native batch insert
    on Postgres; iterates the helper on other dialects. Caller commits.
    """
    if not rows:
        return 0
    dialect_name = session.bind.dialect.name if session.bind else ""
    conflict_cols = list(conflict_columns)

    if dialect_name == "postgresql":
        from sqlalchemy.dialects.postgresql import insert as pg_insert

        stmt = pg_insert(model).values(rows)
        set_cols = (
            list(update_columns)
            if update_columns is not None
            else [c for c in rows[0] if c not in conflict_cols]
        )
        set_dict = {c: getattr(stmt.excluded, c) for c in set_cols}
        if set_dict:
            stmt = stmt.on_conflict_do_update(index_elements=conflict_cols, set_=set_dict)
        else:
            stmt = stmt.on_conflict_do_nothing(index_elements=conflict_cols)
        result = session.execute(stmt)
        return result.rowcount or len(rows)

    count = 0
    for row in rows:
        try:
            upsert(session, model, conflict_cols, row, update_columns)
            count += 1
        except SQLAlchemyError as exc:
            logger.warning("bulk_upsert row failed on %s: %s", model.__name__, exc)
    return count
