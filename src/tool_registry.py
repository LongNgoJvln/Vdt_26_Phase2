"""Canonical registry and per-session tri-state preferences for all tools."""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Any, Iterable

from core.app_profile import profile


VALID_MODES = frozenset({"disabled", "auto", "pinned"})
_LOCK = threading.RLock()
_PREF_PATH = Path(os.getenv("TOOL_PREFERENCES_PATH", "data/tool_preferences.json"))


def builtin_id(name: str) -> str:
    return f"builtin:{name}"


def mcp_id(server_id: str, name: str) -> str:
    return f"mcp:{server_id}:{name}"


def _scope(owner: str | None, session_id: str | None) -> tuple[str, str]:
    return (owner or "__local__", session_id or "__default__")


def _read_preferences() -> dict[str, Any]:
    try:
        data = json.loads(_PREF_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return {}


def _write_preferences(data: dict[str, Any]) -> None:
    _PREF_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = _PREF_PATH.with_suffix(_PREF_PATH.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, _PREF_PATH)


def get_preferences(owner: str | None, session_id: str | None) -> dict[str, str]:
    owner_key, session_key = _scope(owner, session_id)
    with _LOCK:
        data = _read_preferences()
        defaults = data.get(owner_key, {}).get("__default__", {})
        scoped = data.get(owner_key, {}).get(session_key, {})
        merged = {**defaults, **scoped}
        return {k: v for k, v in merged.items() if v in VALID_MODES}


def set_preferences(
    owner: str | None,
    session_id: str | None,
    updates: dict[str, str],
) -> dict[str, str]:
    invalid = {key: mode for key, mode in updates.items() if mode not in VALID_MODES}
    if invalid:
        raise ValueError(f"Invalid tool mode(s): {invalid}")
    owner_key, session_key = _scope(owner, session_id)
    with _LOCK:
        data = _read_preferences()
        owner_data = data.setdefault(owner_key, {})
        current = owner_data.setdefault(session_key, {})
        current.update(updates)
        _write_preferences(data)
    return get_preferences(owner, session_id)


def build_registry(mcp_manager=None, mcp_tools: Iterable[dict] | None = None) -> list[dict]:
    """Build one serialisable registry for built-in and MCP tools.

    Registry IDs are stable and collision-free even when two MCP servers
    expose tools with the same short name.
    """
    from src.agent_tools import FUNCTION_TOOL_SCHEMAS

    blocked = profile.blocked_builtin_tools()
    try:
        from src.settings import get_setting
        global_disabled = set(get_setting("disabled_tools", []) or [])
    except Exception:
        global_disabled = set()
    entries: list[dict] = []
    for schema in FUNCTION_TOOL_SCHEMAS:
        fn = schema.get("function") or {}
        name = str(fn.get("name") or "").strip()
        if not name or name in blocked:
            continue
        entries.append({
            "id": builtin_id(name),
            "name": name,
            "execution_name": name,
            "source": "builtin",
            "provider": "Network Change",
            "description": fn.get("description") or "",
            "schema": fn.get("parameters") or {"type": "object", "properties": {}},
            "globally_enabled": name not in global_disabled,
        })

    raw_mcp = list(mcp_tools) if mcp_tools is not None else (
        mcp_manager.get_all_tools() if mcp_manager is not None else []
    )
    for tool in raw_mcp:
        server_id = str(tool.get("server_id") or "")
        name = str(tool.get("name") or "")
        if not server_id or not name:
            continue
        entries.append({
            "id": mcp_id(server_id, name),
            "name": name,
            "execution_name": tool.get("qualified_name") or f"mcp__{server_id}__{name}",
            "source": "mcp",
            "provider": tool.get("server_name") or server_id,
            "server_id": server_id,
            "description": tool.get("description") or "",
            "schema": tool.get("input_schema") or {"type": "object", "properties": {}},
            "globally_enabled": not bool(tool.get("is_disabled")),
        })
    return sorted(entries, key=lambda item: (item["source"], item["provider"].lower(), item["name"].lower()))


def accessible_mcp_tools(
    mcp_manager,
    owner: str | None,
    disabled_map: dict[str, set] | None = None,
) -> list[dict]:
    """Return only connected MCP tools visible to ``owner``.

    Owner-less MCP servers are shared.  An owner-less request can only see
    shared servers; authenticated users can additionally see their own rows.
    """
    from core.database import McpServer, SessionLocal

    db = SessionLocal()
    try:
        query = db.query(McpServer)
        if owner:
            query = query.filter(
                (McpServer.owner == owner) | McpServer.owner.is_(None)
            )
        else:
            query = query.filter(McpServer.owner.is_(None))
        rows = query.all()
        allowed_ids = {row.id for row in rows}
    finally:
        db.close()
    effective_disabled = {
        server_id: set(names) for server_id, names in (disabled_map or {}).items()
    }
    for row in rows:
        try:
            names = json.loads(row.disabled_tools or "[]")
        except (TypeError, json.JSONDecodeError):
            names = []
        if names:
            effective_disabled.setdefault(row.id, set()).update(names)
    return [
        tool for tool in mcp_manager.get_all_tools(effective_disabled)
        if tool.get("server_id") in allowed_ids
    ]


def apply_preferences(entries: list[dict], owner: str | None, session_id: str | None) -> list[dict]:
    prefs = get_preferences(owner, session_id)
    result = []
    for raw in entries:
        item = dict(raw)
        if not item.get("globally_enabled", True):
            mode = "disabled"
            locked = True
        else:
            mode = prefs.get(item["id"], "auto")
            locked = False
        item["mode"] = mode
        item["locked"] = locked
        result.append(item)
    return result


def execution_sets(entries: list[dict], owner: str | None, session_id: str | None) -> tuple[set[str], set[str]]:
    """Return ``(disabled_execution_names, pinned_execution_names)``."""
    disabled: set[str] = set()
    pinned: set[str] = set()
    for item in apply_preferences(entries, owner, session_id):
        name = item["execution_name"]
        if item["mode"] == "disabled":
            disabled.add(name)
        elif item["mode"] == "pinned":
            pinned.add(name)
    return disabled, pinned
