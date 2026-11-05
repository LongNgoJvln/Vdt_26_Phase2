"""Research background task routes — /api/research/*."""

import asyncio
import json
import logging
import re
import uuid
from datetime import datetime
from core.time_utils import utcnow_naive
from typing import Optional

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
from src.endpoint_resolver import resolve_endpoint
from src.auth_helpers import _auth_disabled, get_current_user
from services.research import research_store

_SESSION_ID_RE = re.compile(r"^[a-zA-Z0-9-]{1,128}$")

logger = logging.getLogger(__name__)

# Model-name substrings that are NOT chat/generation models — research must
# never pick these as its model. An OpenAI-style endpoint often lists
# `text-embedding-ada-002` etc. first in its model list, which is why research
# was failing with "Cannot reach model 'text-embedding-ada-002'".
_NON_CHAT_MODEL = (
    "text-embedding", "embedding", "tts-", "whisper", "dall-e",
    "moderation", "rerank", "reranker", "clip", "stable-diffusion",
)


def _first_chat_model(models) -> str:
    """First model that isn't an embedding/tts/etc. — falls back to models[0]."""
    for m in (models or []):
        if not any(p in str(m).lower() for p in _NON_CHAT_MODEL):
            return m
    return (models[0] if models else "")


def _resolve_research_endpoint(sess) -> tuple:
    """Return (endpoint_url, model, headers) for Deep Research, checking admin overrides."""
    url, model, headers = resolve_endpoint(
        "research",
        fallback_url=sess.endpoint_url,
        fallback_model=sess.model,
        fallback_headers=sess.headers,
    )
    return url, model, headers


def setup_research_routes(research_handler, session_manager=None) -> APIRouter:
    router = APIRouter(tags=["research"])

    def _require_user(request: Request) -> str:
        """All research endpoints require an authenticated user. Research
        data isn't owner-scoped in the on-disk JSON yet, so we at least
        block anonymous access. Multi-tenant deploys should additionally
        verify the session belongs to this user."""
        user = get_current_user(request)
        if not user:
            if _auth_disabled():
                return ""
            raise HTTPException(401, "Not authenticated")
        return user

    def _validate_session_id(session_id: str) -> None:
        if not _SESSION_ID_RE.fullmatch(session_id):
            raise HTTPException(400, "Invalid session ID format")

    def _owns_in_memory(session_id: str, user: str) -> bool:
        """Ownership check for an in-flight (in-memory) research task.
        Falls back to the persisted store if the task has already finished."""
        entry = research_handler._active_tasks.get(session_id)
        if entry is not None:
            return entry.get("owner", "") == user
        # Task no longer in memory — consult the per-owner store. The store
        # enforces owner scope itself (foreign rows surface as None), so a
        # truthy return here means both "row exists" and "row belongs to user".
        data = research_store.load(user, session_id)
        return data is not None

    @router.get("/api/research/active")
    async def research_active(request: Request):
        """List all currently active (running) research tasks."""
        user = _require_user(request)
        active = []
        for sid, entry in research_handler._active_tasks.items():
            # SECURITY: only show this user's running tasks.
            if entry.get("owner", "") != user:
                continue
            if entry.get("status") == "running":
                active.append({
                    "session_id": sid,
                    "query": entry.get("query", ""),
                    "status": "running",
                    "progress": entry.get("progress", {}),
                    "started_at": entry.get("started_at", 0),
                })
        return {"active": active}

    @router.get("/api/research/status/{session_id}")
    async def research_status(session_id: str, request: Request):
        user = _require_user(request)
        _validate_session_id(session_id)
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research found for this session")
        status = research_handler.get_status(session_id, owner=user)
        if status is None:
            raise HTTPException(404, "No research found for this session")
        return status

    @router.post("/api/research/cancel/{session_id}")
    async def research_cancel(session_id: str, request: Request):
        user = _require_user(request)
        _validate_session_id(session_id)
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research found for this session")
        cancelled = research_handler.cancel_research(session_id)
        return {"cancelled": cancelled}

    @router.post("/api/research/result/{session_id}")
    async def research_result(session_id: str, request: Request):
        user = _require_user(request)
        _validate_session_id(session_id)
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research result available")
        result = research_handler.get_result(session_id, owner=user)
        if result is None:
            raise HTTPException(404, "No research result available")
        sources = research_handler.get_sources(session_id, owner=user) or []
        raw_findings = research_handler.get_raw_findings(session_id, owner=user) or []
        research_handler.clear_result(session_id, owner=user)
        return {"result": result, "sources": sources, "raw_findings": raw_findings}

    def _assert_owns_research(session_id: str, user: str) -> None:
        """404-not-403 ownership gate for a research session's persisted row.
        Use BEFORE returning any data or mutating the row. research_store
        returns None for foreign rows as well as missing ones, so this gate
        leaks no information about whether the session exists for someone
        else."""
        if research_store.load(user, session_id) is None:
            raise HTTPException(404, "Research not found")

    @router.get("/api/research/report/{session_id}")
    async def research_report(session_id: str, request: Request):
        """Serve the visual HTML report for a completed research session."""
        user = _require_user(request)
        _validate_session_id(session_id)
        _assert_owns_research(session_id, user)
        logger.info(f"Visual report requested for session {session_id}")
        try:
            html_content = research_handler.get_report_html(session_id, owner=user)
        except Exception as e:
            logger.error(f"Visual report generation error: {e}", exc_info=True)
            raise HTTPException(500, f"Report generation failed: {e}")
        if html_content is None:
            logger.warning(f"No report data found for session {session_id}")
            raise HTTPException(404, "No visual report available for this session")
        return HTMLResponse(content=html_content)

    class HideImageRequest(BaseModel):
        url: str

    @router.post("/api/research/{session_id}/hide-image")
    async def research_hide_image(session_id: str, body: HideImageRequest, request: Request):
        """Mark an image URL as hidden for this research's visual report.
        Persisted to the research JSON so subsequent /report renders skip it."""
        user = _require_user(request)
        _validate_session_id(session_id)
        _assert_owns_research(session_id, user)
        ok = research_handler.hide_image(session_id, body.url, owner=user)
        if not ok:
            raise HTTPException(404, "Research not found")
        return {"ok": True}

    @router.post("/api/research/{session_id}/unhide-images")
    async def research_unhide_images(session_id: str, request: Request):
        """Clear the hidden-images list for a research session."""
        user = _require_user(request)
        _validate_session_id(session_id)
        _assert_owns_research(session_id, user)
        ok = research_handler.unhide_all_images(session_id, owner=user)
        if not ok:
            raise HTTPException(404, "Research not found")
        return {"ok": True}

    @router.get("/api/research/library")
    async def research_library(
        request: Request,
        search: Optional[str] = Query(None),
        sort: str = Query("recent"),
        limit: int = Query(50),
        archived: bool = Query(False),
    ):
        user = _require_user(request)
        """List all completed research for the Library panel."""
        items = []
        # research_store.list_ids already filters to this owner — no extra
        # owner check needed below.
        for rid in research_store.list_ids(user):
            try:
                d = research_store.load(user, rid)
                if not d:
                    continue
                # Archived view shows ONLY archived reports; default hides them.
                if bool(d.get("archived")) != archived:
                    continue
                query = d.get("query", "")
                if search and search.lower() not in query.lower():
                    continue
                sources = d.get("sources", [])
                items.append({
                    "id": rid,
                    "query": query,
                    "category": d.get("category") or "",
                    "source_count": len(sources),
                    "status": d.get("status", "done"),
                    "duration": d.get("stats", {}).get("Duration", ""),
                    "rounds": d.get("stats", {}).get("Rounds", ""),
                    "started_at": d.get("started_at", 0),
                    "completed_at": d.get("completed_at", 0),
                    "archived": bool(d.get("archived")),
                })
            except Exception:
                continue

        # Sort
        if sort == "recent":
            items.sort(key=lambda x: x["completed_at"] or 0, reverse=True)
        elif sort == "oldest":
            items.sort(key=lambda x: x["completed_at"] or 0)
        elif sort == "most-messages":
            items.sort(key=lambda x: x["source_count"], reverse=True)
        elif sort == "alpha":
            items.sort(key=lambda x: x["query"].lower())

        return {"research": items[:limit], "total": len(items)}

    @router.get("/api/research/detail/{session_id}")
    async def research_detail(session_id: str, request: Request):
        """Return the full JSON for a single research result — sources,
        summary, stats — used by the Library preview panel."""
        user = _require_user(request)
        _validate_session_id(session_id)
        # research_store returns None for foreign rows too — keep a single
        # 404 path so the error is identical for "missing" and "not yours".
        data = research_store.load(user, session_id)
        if data is None:
            raise HTTPException(404, "Research not found")
        return data

    @router.post("/api/research/{session_id}/archive")
    async def research_archive(session_id: str, request: Request, archived: bool = Query(True)):
        """Soft-archive / restore a research report (sets `archived` in its row)."""
        user = _require_user(request)
        _validate_session_id(session_id)
        try:
            data = research_store.load(user, session_id)
            if data is None:
                raise HTTPException(404, "Research not found")
            data["archived"] = bool(archived)
            research_store.save(user, session_id, data)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(500, f"Failed to update research: {e}")
        return {"ok": True, "id": session_id, "archived": bool(archived)}

    @router.delete("/api/research/{session_id}")
    async def research_delete(session_id: str, request: Request):
        """Delete a research result from the store."""
        user = _require_user(request)
        _validate_session_id(session_id)
        # Same 404-not-403 invariant as detail/archive: a foreign row
        # must surface identically to a missing one so the caller can't
        # probe ids by id. delete() is owner-scoped so it would no-op
        # anyway, but the load check is what makes the response uniform.
        if research_store.load(user, session_id) is None:
            raise HTTPException(status_code=404, detail="Research not found")
        research_store.delete(user, session_id)
        return {"deleted": True}

    # ------------------------------------------------------------------
    # Panel endpoints — launch research without a chat session
    # ------------------------------------------------------------------

    class ResearchStartRequest(BaseModel):
        query: str
        # max_rounds=0 means "Auto" — let the AI decide when to stop, capped at 20.
        max_rounds: int = Field(default=0, ge=0, le=20)
        search_provider: Optional[str] = None
        endpoint_id: Optional[str] = None
        model: Optional[str] = None
        max_time: int = Field(default=300, ge=60, le=1800)
        extraction_timeout: Optional[int] = Field(default=None, ge=15, le=3600)
        extraction_concurrency: Optional[int] = Field(default=None, ge=1, le=12)
        category: Optional[str] = None

    @router.post("/api/research/start")
    async def research_start(body: ResearchStartRequest, request: Request):
        """Launch a research job from the dedicated panel."""
        from src.auth_helpers import require_privilege
        user = require_privilege(request, "can_use_research")
        if user == "internal-tool":
            tool_owner = (request.headers.get("X-VHTNA-Owner") or "").strip()
            if tool_owner and tool_owner not in {"internal-tool", "api", "demo", "system"}:
                auth_mgr = getattr(request.app.state, "auth_manager", None)
                if auth_mgr is not None and getattr(auth_mgr, "is_configured", False):
                    try:
                        privs = auth_mgr.get_privileges(tool_owner) or {}
                        if not privs.get("can_use_research", True):
                            raise HTTPException(403, f"Your account is not allowed to can use research.")
                    except HTTPException:
                        raise
                    except Exception:
                        pass
                user = tool_owner
        session_id = f"rp-{uuid.uuid4().hex[:12]}"

        if body.endpoint_id:
            from src.database import SessionLocal
            from src.database import ModelEndpoint
            from src.endpoint_resolver import normalize_base, build_chat_url, build_headers
            db = SessionLocal()
            try:
                ep = db.query(ModelEndpoint).filter(
                    ModelEndpoint.id == body.endpoint_id,
                    ModelEndpoint.is_enabled == True,
                ).first()
                if not ep:
                    raise HTTPException(404, "Endpoint not found or disabled")
                base = normalize_base(ep.base_url)
                ep_url = build_chat_url(base)
                ep_headers = build_headers(ep.api_key, base)
                ep_model = body.model or ""
                if not ep_model:
                    try:
                        import json as _json
                        models = _json.loads(ep.cached_models) if ep.cached_models else []
                        if models:
                            ep_model = _first_chat_model(models)
                    except Exception:
                        pass
            finally:
                db.close()
        else:
            ep_url, ep_model, ep_headers = resolve_endpoint("research")
            if not ep_url:
                ep_url, ep_model, ep_headers = resolve_endpoint("utility")
            # When neither research nor utility is configured, use the user's
            # configured DEFAULT model (default_endpoint_id/default_model) rather
            # than arbitrarily grabbing the first enabled endpoint's first model
            # (which surfaced gpt-3.5). "Default" should mean the default model.
            if not ep_url:
                ep_url, ep_model, ep_headers = resolve_endpoint("default")
            if not ep_url:
                ep_url, ep_model, ep_headers = resolve_endpoint("chat")
            if not ep_url:
                from src.database import SessionLocal
                from src.database import ModelEndpoint
                from src.endpoint_resolver import normalize_base, build_chat_url, build_headers
                db = SessionLocal()
                try:
                    ep = db.query(ModelEndpoint).filter(
                        ModelEndpoint.is_enabled == True,
                    ).first()
                    if ep:
                        base = normalize_base(ep.base_url)
                        ep_url = build_chat_url(base)
                        ep_headers = build_headers(ep.api_key, base)
                        ep_model = ""
                        if ep.cached_models:
                            try:
                                import json as _json
                                models = _json.loads(ep.cached_models)
                                if models:
                                    ep_model = _first_chat_model(models)
                            except Exception:
                                pass
                finally:
                    db.close()
            if not ep_url:
                raise HTTPException(400, "No endpoints configured. Add one in Settings first.")
            if body.model:
                ep_model = body.model

        # max_rounds=0 → "Auto", let AI decide; pass 20 as the safety cap.
        effective_max_rounds = body.max_rounds if body.max_rounds > 0 else 20
        research_handler.start_research(
            session_id=session_id,
            query=body.query,
            llm_endpoint=ep_url,
            llm_model=ep_model,
            max_time=body.max_time,
            llm_headers=ep_headers,
            max_rounds=effective_max_rounds,
            search_provider=body.search_provider or None,
            category=body.category or None,
            extraction_timeout=body.extraction_timeout,
            extraction_concurrency=body.extraction_concurrency,
            owner=user,
        )
        return {"session_id": session_id, "status": "running", "query": body.query}

    @router.get("/api/research/stream/{session_id}")
    async def research_stream(session_id: str, request: Request):
        """SSE stream of research progress events."""
        user = _require_user(request)
        _validate_session_id(session_id)
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research found for this session")
        async def _generate():
            last_progress = None
            while True:
                status = research_handler.get_status(session_id, owner=user)
                if status is None:
                    yield f"data: {json.dumps({'status': 'not_found'})}\n\n"
                    return
                st = status.get("status", "")
                progress = status.get("progress", {})
                if progress != last_progress:
                    last_progress = progress
                    yield f"data: {json.dumps({**progress, 'status': st})}\n\n"
                if st != "running":
                    final = {'status': st, 'final': True}
                    task = research_handler._active_tasks.get(session_id, {})
                    if st == "error" and task.get("result"):
                        final['error'] = str(task["result"])[:500]
                    yield f"data: {json.dumps(final)}\n\n"
                    return
                await asyncio.sleep(1.5)

        return StreamingResponse(
            _generate(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @router.post("/api/research/result-peek/{session_id}")
    async def research_result_peek(session_id: str, request: Request):
        """Get research result without clearing it (for panel use)."""
        user = _require_user(request)
        _validate_session_id(session_id)
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research found for this session")
        # The handler + research_store now resolve the row owner-scoped, so
        # there's no need for a separate path-based fallback here. If the
        # in-memory task is gone and the store has nothing, the row is gone.
        result = research_handler.get_result(session_id, owner=user)
        if result is None:
            data = research_store.load(user, session_id)
            if data:
                return {
                    "result": data.get("result", ""),
                    "sources": data.get("sources", []),
                    "raw_findings": data.get("raw_findings", []),
                    "category": data.get("category") or "",
                }
            raise HTTPException(404, "No research result available")
        sources = research_handler.get_sources(session_id, owner=user) or []
        raw_findings = research_handler.get_raw_findings(session_id, owner=user) or []
        return {"result": result, "sources": sources, "raw_findings": raw_findings, "category": ""}

    @router.post("/api/research/spinoff/{session_id}")
    async def research_spinoff(session_id: str, request: Request):
        """Create a new chat session pre-seeded with this research as context.

        Reads the persisted research result + sources for `session_id`, creates
        a fresh session (inheriting endpoint/model/headers from the source
        session if available, otherwise from the resolved chat endpoint), and
        injects a single system message containing the report and sources so
        the user can ask follow-up questions in a clean conversation.
        """
        user = _require_user(request)
        _validate_session_id(session_id)
        # SECURITY: gate on ownership before reading the persisted research —
        # otherwise any authenticated user could spin off (and thereby read)
        # another user's report by guessing its session ID. Mirrors every other
        # endpoint in this file (see result_peek above).
        if not _owns_in_memory(session_id, user):
            raise HTTPException(404, "No research found for this session")
        if session_manager is None:
            raise HTTPException(500, "session_manager not configured")

        # Load research data — prefer in-memory result, fall back to the
        # per-owner store (research_handler.* methods already accept owner=).
        result = research_handler.get_result(session_id, owner=user)
        sources = research_handler.get_sources(session_id, owner=user) or []
        query = ""

        disk = research_store.load(user, session_id) or {}
        if disk:
            if not result:
                result = disk.get("result")
            if not sources:
                sources = disk.get("sources", []) or []
            query = disk.get("query", "") or ""

        if not result:
            raise HTTPException(404, "No research result available for this session")

        # Inherit endpoint/model/headers from the source session when possible.
        # For panel-launched research (rp-* IDs), there is no chat session, so
        # fall back through the same chain as /api/research/start: research →
        # utility → first enabled endpoint in the DB.
        ep_url, ep_model, ep_headers = "", "", {}
        try:
            src_sess = session_manager.get_session(session_id)
            ep_url = src_sess.endpoint_url or ""
            ep_model = src_sess.model or ""
            ep_headers = dict(src_sess.headers or {})
        except KeyError:
            pass

        def _merge(r_url, r_model, r_headers):
            nonlocal ep_url, ep_model, ep_headers
            if not ep_url and r_url:
                ep_url = r_url
            if not ep_model and r_model:
                ep_model = r_model
            if not ep_headers and r_headers:
                ep_headers = dict(r_headers)

        if not ep_url or not ep_model:
            _merge(*resolve_endpoint("chat"))
        if not ep_url or not ep_model:
            _merge(*resolve_endpoint("research"))
        if not ep_url or not ep_model:
            _merge(*resolve_endpoint("utility"))
        if not ep_url or not ep_model:
            # Last resort: any enabled endpoint
            from src.database import SessionLocal
            from src.database import ModelEndpoint
            from src.endpoint_resolver import normalize_base, build_chat_url, build_headers
            db = SessionLocal()
            try:
                ep = db.query(ModelEndpoint).filter(ModelEndpoint.is_enabled == True).first()
                if ep:
                    base = normalize_base(ep.base_url)
                    fallback_url = build_chat_url(base)
                    fallback_headers = build_headers(ep.api_key, base)
                    fallback_model = ""
                    if ep.cached_models:
                        try:
                            models = json.loads(ep.cached_models)
                            if models:
                                fallback_model = models[0]
                        except Exception:
                            pass
                    _merge(fallback_url, fallback_model, fallback_headers)
            finally:
                db.close()

        if not ep_url or not ep_model:
            raise HTTPException(400, "No endpoint configured — add one in Settings first")

        # Create new session
        new_sid = str(uuid.uuid4())

        title_query = (query or "research").strip()
        if len(title_query) > 60:
            title_query = title_query[:57] + "…"
        new_name = f"Follow-up: {title_query}"

        new_sess = session_manager.create_session(
            session_id=new_sid,
            name=new_name,
            endpoint_url=ep_url,
            model=ep_model,
            rag=False,
            owner=user,
        )
        if ep_headers:
            new_sess.headers = ep_headers
            session_manager.save_sessions()
        try:
            from src.event_bus import fire_event
            fire_event("session_created", user)
        except Exception:
            logger.debug("session_created event dispatch failed", exc_info=True)

        # Build the priming system message — report only, no sources injected.
        # The user can open the visual report for source details; keeping sources
        # out of the chat context saves tokens and avoids the AI fabricating
        # citations.
        date_str = utcnow_naive().strftime("%Y-%m-%d")
        primer = (
            f"[Research context — {date_str}]\n\n"
            f"The user previously ran a deep research investigation. Use the "
            f"report below as your primary knowledge base when answering "
            f"follow-up questions. If the user asks something not covered, "
            f"say so plainly rather than guessing.\n\n"
            f"=== ORIGINAL QUERY ===\n{query or '(not recorded)'}\n\n"
            f"=== REPORT ===\n{result}"
        )

        from core.models import ChatMessage
        new_sess.add_message(ChatMessage(
            role="system",
            content=primer,
            metadata={"research_spinoff_from": session_id},
        ))
        session_manager.save_sessions()

        return {
            "session_id": new_sid,
            "name": new_name,
            "source_count": len(sources),
        }

    return router
