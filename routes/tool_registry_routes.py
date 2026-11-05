"""Unified built-in/MCP tool registry API used by the chat composer."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from core.database import Session, SessionLocal
from src.auth_helpers import effective_user, require_user
from src.tool_registry import (
    accessible_mcp_tools,
    apply_preferences,
    build_registry,
    set_preferences,
)


def setup_tool_registry_routes(mcp_manager) -> APIRouter:
    router = APIRouter(prefix="/api/tool-registry", tags=["tool-registry"])

    def _assert_session_owner(owner: str, session_id: str | None) -> None:
        if not session_id:
            return
        db = SessionLocal()
        try:
            row = db.query(Session).filter(Session.id == session_id).first()
            if row is None:
                raise HTTPException(404, "Session not found")
            if owner and row.owner not in (None, owner):
                raise HTTPException(403, "Session belongs to another user")
        finally:
            db.close()

    @router.get("")
    def list_registry(request: Request, session_id: str | None = None):
        require_user(request)
        owner = effective_user(request) or ""
        _assert_session_owner(owner, session_id)
        entries = build_registry(mcp_tools=accessible_mcp_tools(mcp_manager, owner))
        return {
            "profile": "network_change",
            "session_id": session_id,
            "tools": apply_preferences(entries, owner, session_id),
        }

    @router.put("/preferences")
    async def update_preferences(request: Request):
        require_user(request)
        owner = effective_user(request) or ""
        body = await request.json()
        session_id = body.get("session_id")
        updates = body.get("tools")
        if not isinstance(updates, dict) or not updates:
            raise HTTPException(400, "tools must be a non-empty object")
        _assert_session_owner(owner, session_id)
        entries = build_registry(mcp_tools=accessible_mcp_tools(mcp_manager, owner))
        allowed_ids = {entry["id"] for entry in entries if entry.get("globally_enabled", True)}
        unknown = set(updates) - allowed_ids
        if unknown:
            raise HTTPException(400, f"Unknown or globally disabled tool IDs: {sorted(unknown)}")
        try:
            prefs = set_preferences(owner, session_id, {str(k): str(v) for k, v in updates.items()})
        except ValueError as exc:
            raise HTTPException(400, str(exc)) from exc
        return {"ok": True, "preferences": prefs}

    return router
