"""Static validation API for network CLI/manifest documents in the editor."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from core.database import Document, SessionLocal
from routes.document_helpers import _verify_doc_owner
from src.auth_helpers import get_current_user, require_user
from src.network_change_tools import _validate_artifact_data


def setup_network_validation_routes() -> APIRouter:
    router = APIRouter(prefix="/api/network-change", tags=["network-validation"])

    @router.post("/validate-document/{doc_id}")
    def validate_document(doc_id: str, request: Request):
        require_user(request)
        user = get_current_user(request)
        db = SessionLocal()
        try:
            doc = db.query(Document).filter(Document.id == doc_id).first()
            if not doc:
                raise HTTPException(404, "Document not found")
            _verify_doc_owner(db, doc, user)
            language = (doc.language or "text").lower()
            fmt = "kubernetes" if language in {"yaml", "kubernetes"} else "network-cli"
            return _validate_artifact_data({"format": fmt, "content": doc.current_content})
        finally:
            db.close()

    return router

