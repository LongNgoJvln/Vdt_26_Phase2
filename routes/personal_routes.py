# routes/personal_routes.py
"""Routes for personal documents management."""
import asyncio
import os
import logging
from typing import List
from fastapi import APIRouter, HTTPException, Query, Request, UploadFile, File, Depends
from src.request_models import DirectoryRequest
from core.constants import BASE_DIR, PERSONAL_DIR
from src.rag_singleton import get_rag_manager
from src.auth_helpers import get_current_user, require_user
from core.middleware import require_admin

UPLOADS_DIR = os.path.join(BASE_DIR, "data", "personal_uploads")
MAX_PERSONAL_UPLOAD_BYTES = int(
    os.getenv("VHTNA_PERSONAL_UPLOAD_MAX_BYTES", str(25 * 1024 * 1024))
)

logger = logging.getLogger(__name__)

def setup_personal_routes(personal_docs_manager, rag_manager, rag_available, upload_handler=None):
    """
    Setup personal documents related routes.

    Args:
        personal_docs_manager: PersonalDocsManager instance
        rag_manager: RAG manager instance (may be None)
        rag_available: Boolean indicating if RAG is available
        upload_handler: UploadHandler for canonical library upload path
            (MinIO + DB row). If None, /api/personal/upload returns 503.

    Returns:
        APIRouter instance with personal docs routes
    """
    router = APIRouter(prefix="/api/personal")

    def _rag():
        """Get the current RAG manager, retrying init if needed."""
        return get_rag_manager()

    def _resolve_allowed_personal_dir(directory: str) -> str:
        """Resolve a user-supplied personal-docs path under the allowed root."""
        if not directory:
            raise HTTPException(400, "Directory path is required")

        base_abs = os.path.abspath(PERSONAL_DIR)
        candidate = directory if os.path.isabs(directory) else os.path.join(base_abs, directory)
        resolved = os.path.abspath(candidate)
        try:
            in_base = os.path.commonpath([resolved, base_abs]) == base_abs
        except ValueError:
            in_base = False
        if not in_base:
            raise HTTPException(403, "Directory must be inside personal documents")
        return resolved
    
    @router.get("")
    def api_personal_list(owner: str = Depends(require_user), _admin: None = Depends(require_admin)):
        """Enhanced version that includes directories"""
        files = [{"name": f["name"], "size": f["size"], "path": f.get("path", "")} for f in personal_docs_manager.index]
        directories = personal_docs_manager.get_indexed_directories() if hasattr(personal_docs_manager, "get_indexed_directories") else []
        return {"files": files, "directories": directories}
    
    @router.post("/reload")
    def api_personal_reload(owner: str = Depends(require_user), _admin: None = Depends(require_admin)):
        personal_docs_manager.refresh_index()
        return {"ok": True, "count": len(personal_docs_manager.index)}
    
    @router.post("/add_directory")
    async def add_directory_to_rag(
        request: Request,
        directory_request: DirectoryRequest,
        owner: str = Depends(require_user), _admin: None = Depends(require_admin),
    ):
        """
        Add a directory and all its subdirectories/files to the RAG index.
        
        Args:
            directory_request: Directory request model containing the directory path
            
        Returns:
            JSON response with indexing results
        """
        directory = directory_request.directory
        try:
            directory = _resolve_allowed_personal_dir(directory)
            
            # Security check - ensure directory exists and is accessible
            if not os.path.exists(directory):
                raise HTTPException(404, f"Directory not found: {directory}")
            
            if not os.path.isdir(directory):
                raise HTTPException(400, f"Path is not a directory: {directory}")
            
            logger.info(f"Adding directory to RAG: {directory}")
            
            # Use the RAGManager to index the directory
            rag = _rag()
            if rag:
                result = rag.index_personal_documents(directory, owner=owner)
                
                if result["success"]:
                    # Also update the personal_docs_manager to track this directory
                    personal_docs_manager.add_directory(directory, index=False)
                    
                    return {
                        "success": True,
                        "message": f"Successfully indexed {result['indexed_count']} chunks from {directory}",
                        "indexed_count": result["indexed_count"],
                        "failed_count": result.get("failed_count", 0),
                        "directory": directory
                    }
                else:
                    raise HTTPException(500, result.get("message", "Failed to index directory"))
            else:
                raise HTTPException(503, "RAG system is not available")
                
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error adding directory to RAG: {e}")
            raise HTTPException(500, f"Failed to add directory: {str(e)}")
    
    @router.delete("/remove_directory")
    async def remove_directory_from_rag(directory: str = Query(...), owner: str = Depends(require_user), _admin: None = Depends(require_admin)):
        """
        Remove a directory from the RAG index.

        Args:
            directory: Path to the directory to remove

        Returns:
            JSON response confirming removal
        """
        try:
            if not directory:
                raise HTTPException(400, "Directory path is required")

            logger.info(f"Removing directory from RAG: {directory}")

            # Always remove from personal_docs_manager tracking
            if hasattr(personal_docs_manager, 'remove_directory'):
                personal_docs_manager.remove_directory(directory)

            # Remove from RAG vector store (best-effort)
            rag = _rag()
            if rag:
                try:
                    rag.remove_directory(directory)
                except Exception as e:
                    logger.warning(f"RAG removal failed for directory {directory}: {e}")

            return {
                "success": True,
                "message": f"Successfully removed {directory} from RAG index",
                "directory": directory
            }

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error removing directory from RAG: {e}")
            raise HTTPException(500, f"Failed to remove directory: {str(e)}")
    
    @router.post("/upload")
    async def upload_files_to_rag(request: Request, files: List[UploadFile] = File(...)):
        """Upload files into RAG via the canonical upload path.

        Consolidates with ``POST /api/upload``: bytes land in MinIO + a DB
        Upload row, then ``ingest_upload_to_rag`` runs fire-and-forget to
        chunk and embed into the per-owner RAG collection. Response shape is
        preserved for backward compat (`{uploaded, indexed_count, failed_count}`).
        """
        if upload_handler is None:
            raise HTTPException(503, "Upload handler is not available")

        user = get_current_user(request)
        client_ip = request.client.host if request.client else "unknown"
        from src.ingest import ingest_upload_to_rag
        from src.rag_singleton import get_rag_manager

        total_indexed = 0  # legacy field — no longer populated synchronously
        total_failed = 0
        uploaded_files = []

        for upload in files:
            try:
                upload.file.seek(0, 2)
                size = upload.file.tell()
                upload.file.seek(0)
                if size > MAX_PERSONAL_UPLOAD_BYTES:
                    logger.warning(f"Rejected oversized personal upload: {upload.filename!r}")
                    total_failed += 1
                    continue

                meta = upload_handler.save_upload(
                    upload, client_ip, owner=user, file_scope="library",
                )
                uploaded_files.append(meta.get("name") or upload.filename)

                vector_rag = get_rag_manager()
                if vector_rag is None:
                    logger.warning(
                        "personal/upload: vector_rag unavailable, ingest deferred for %s",
                        meta.get("id"),
                    )
                else:
                    asyncio.create_task(ingest_upload_to_rag(
                        upload_meta=meta, owner=user,
                        vector_rag=vector_rag,
                        upload_handler=upload_handler,
                    ))
            except Exception as e:
                logger.error(f"Failed to upload {upload.filename}: {e}")
                total_failed += 1

        return {
            "success": True,
            "uploaded": uploaded_files,
            "indexed_count": total_indexed,
            "failed_count": total_failed,
            "ingest_status": "pending" if uploaded_files else None,
        }

    @router.delete("/file")
    async def delete_file_from_rag(filepath: str = Query(...), owner: str = Depends(require_user), _admin: None = Depends(require_admin)):
        """Delete a specific file from RAG index and optionally from disk."""
        try:
            # Remove chunks from RAG vector store (best-effort)
            removed = 0
            rag = _rag()
            if rag:
                try:
                    removed = rag.delete_by_source(filepath)
                except Exception as e:
                    logger.warning(f"RAG removal failed for {filepath}: {e}")

            # Delete file from disk if it's in uploads dir
            deleted_from_disk = False
            try:
                abs_target = os.path.abspath(filepath)
                base_abs = os.path.abspath(UPLOADS_DIR)
                in_uploads = (
                    abs_target == base_abs
                    or os.path.commonpath([abs_target, base_abs]) == base_abs
                )
            except ValueError:
                # commonpath raises on mixed drives / non-comparable paths
                in_uploads = False
            if in_uploads and abs_target != base_abs and os.path.exists(abs_target):
                os.remove(abs_target)
                deleted_from_disk = True

            # Exclude the file from the listing (persists across restarts)
            personal_docs_manager.exclude_file(filepath)

            return {
                "success": True,
                "removed_chunks": removed,
                "deleted_from_disk": deleted_from_disk,
            }
        except Exception as e:
            logger.error(f"Failed to delete file {filepath}: {e}")
            raise HTTPException(500, f"Failed to delete file: {str(e)}")

    return router
