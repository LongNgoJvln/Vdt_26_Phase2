"""Owner-scoped network knowledge ingestion from bundled files or the UI."""

from __future__ import annotations

import asyncio
import re
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from scripts.ingest_network_knowledge import (
    CATEGORIES, DEFAULT_KNOWLEDGE_ROOT, SUPPORTED_EXTENSIONS,
    SourceDocument, discover_documents, ingest_documents,
)
from src.auth_helpers import effective_user, require_user
from src.rag_singleton import get_rag_manager


MAX_UPLOAD = 2 * 1024 * 1024


def _rag_or_503():
    rag = get_rag_manager()
    if not rag or not getattr(rag, "healthy", False):
        raise HTTPException(503, "Knowledge DB unavailable; check QDRANT_URL and embedding configuration")
    return rag


def setup_knowledge_routes() -> APIRouter:
    router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])

    @router.get("/sources")
    def list_sources(request: Request):
        require_user(request)
        documents = discover_documents(DEFAULT_KNOWLEDGE_ROOT, CATEGORIES)
        return {
            "root": str(DEFAULT_KNOWLEDGE_ROOT),
            "counts": {category: sum(d.category == category for d in documents) for category in CATEGORIES},
            "files": [{"category": d.category, "path": d.relative_path} for d in documents],
        }

    @router.post("/ingest")
    async def ingest_bundled(request: Request):
        require_user(request)
        owner = effective_user(request) or "local"
        body = await request.json()
        category = str(body.get("category") or "all")
        if category not in {*CATEGORIES, "all"}:
            raise HTTPException(400, "category must be knowledge, instructions, or all")
        categories = CATEGORIES if category == "all" else (category,)
        documents = discover_documents(DEFAULT_KNOWLEDGE_ROOT, categories)
        result = await asyncio.to_thread(
            ingest_documents, _rag_or_503(), documents, owner, bool(body.get("replace"))
        )
        return {"ok": result["files_failed"] == 0, **result}

    @router.post("/upload")
    async def upload_source(
        request: Request,
        role: str = Form(...),
        replace: bool = Form(True),
        file: UploadFile = File(...),
    ):
        require_user(request)
        owner = effective_user(request) or "local"
        if role not in CATEGORIES:
            raise HTTPException(400, "role must be knowledge or instructions")
        suffix = Path(file.filename or "").suffix.lower()
        if suffix not in SUPPORTED_EXTENSIONS:
            raise HTTPException(400, "Only .md, .txt, and .json are supported")
        content = await file.read(MAX_UPLOAD + 1)
        if len(content) > MAX_UPLOAD:
            raise HTTPException(413, "Knowledge file exceeds 2 MiB")
        safe_name = re.sub(r"[^\w.-]+", "-", Path(file.filename or "source.md").name).strip(".-")
        if not safe_name:
            safe_name = f"source{suffix}"
        owner_dir = re.sub(r"[^\w.-]+", "-", owner).strip(".-") or "local"
        target_dir = DEFAULT_KNOWLEDGE_ROOT / "user" / owner_dir / role
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / safe_name
        target.write_bytes(content)
        document = SourceDocument(role, target, f"user/{owner_dir}/{role}/{safe_name}")
        result = await asyncio.to_thread(ingest_documents, _rag_or_503(), [document], owner, replace)
        return {"ok": result["files_failed"] == 0, "saved_to": str(target), **result}

    return router
