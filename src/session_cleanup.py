"""src/session_cleanup.py

Background worker for cleaning up expired session-scoped files.

This module provides the SessionFileCleanup class which:
1. Finds expired session files based on expires_at timestamp
2. Deletes files from MinIO/object store
3. Removes files from local filesystem
4. Deletes associated RAG embeddings
5. Updates database records

The cleanup is idempotent and safe to retry.
"""

import logging
import os
from datetime import datetime, timezone
from core.time_utils import utcnow, iso_utc
from typing import Dict, Any, List, Optional

from sqlalchemy import text
from core.database import SessionLocal, Document, FileScope
from src.object_store import store as object_store
from src.rag_singleton import get_rag_manager

logger = logging.getLogger(__name__)


class SessionFileCleanup:
    """Background worker for cleaning up expired session files."""

    def __init__(self, ttl_days: int = 7):
        """Initialize the cleanup worker.
        
        Args:
            ttl_days: Default TTL for session files in days
        """
        self.ttl_days = ttl_days
        self._stats = {
            "total_runs": 0,
            "total_files_deleted": 0,
            "total_rag_deleted": 0,
            "total_errors": 0,
            "last_run": None,
        }

    def cleanup_expired_files(self) -> Dict[str, Any]:
        """Run the cleanup process for expired session files.
        
        Returns:
            Dictionary with cleanup statistics
        """
        self._stats["total_runs"] += 1
        self._stats["last_run"] = iso_utc(utcnow())
        
        result = {
            "success": True,
            "files_deleted": 0,
            "rag_deleted": 0,
            "errors": 0,
            "details": [],
        }
        
        try:
            expired_docs = self._get_expired_documents()
            logger.info(f"Found {len(expired_docs)} expired session documents")
            
            for doc in expired_docs:
                try:
                    deleted = self._delete_document(doc)
                    if deleted:
                        result["files_deleted"] += 1
                        self._stats["total_files_deleted"] += 1
                except Exception as e:
                    logger.error(f"Failed to delete document {doc.id}: {e}")
                    result["errors"] += 1
                    self._stats["total_errors"] += 1
                    result["details"].append({
                        "doc_id": doc.id,
                        "error": str(e),
                    })
            
            logger.info(f"Cleanup completed: {result['files_deleted']} files deleted, {result['errors']} errors")
            return result
            
        except Exception as e:
            logger.error(f"Cleanup process failed: {e}")
            result["success"] = False
            result["error"] = str(e)
            self._stats["total_errors"] += 1
            return result

    def _get_expired_documents(self) -> List[Document]:
        """Query database for expired session-scoped documents.
        
        Returns:
            List of Document objects that have expired
        """
        now = utcnow()
        
        with SessionLocal() as db:
            expired = db.query(Document).filter(
                Document.file_scope == FileScope.SESSION.value,
                Document.expires_at != None,
                Document.expires_at < now,
            ).all()
            
            return expired

    def _delete_document(self, doc: Document) -> bool:
        """Delete a single expired document and its associated resources.
        
        Args:
            doc: The Document object to delete
            
        Returns:
            True if deletion was successful
        """
        doc_id = doc.id
        storage_path = doc.storage_path
        
        deleted = False
        
        # Step 1: Delete from RAG (if document was indexed)
        try:
            rag = get_rag_manager()
            if rag:
                rag_source = f"document:{doc_id}"
                if rag.delete_document(rag_source):
                    logger.info(f"Deleted document {doc_id} from RAG")
                    deleted = True
        except Exception as e:
            logger.warning(f"Failed to delete document {doc_id} from RAG: {e}")
        
        # Step 2: Delete from MinIO/object store
        if storage_path and object_store.healthy:
            try:
                # Extract owner and key from storage_path
                # Format: userdata/{owner}/{path} or {owner}/sessions/... or {owner}/library/...
                if storage_path.startswith("userdata/"):
                    parts = storage_path.split("/", 2)
                    if len(parts) >= 3:
                        owner = parts[1]
                        key = parts[2]
                        if object_store.delete_user_object(owner, key):
                            logger.info(f"Deleted {storage_path} from MinIO")
                            deleted = True
                else:
                    # Try direct deletion using session/library methods
                    if "/sessions/" in storage_path:
                        parts = storage_path.split("/")
                        if len(parts) >= 4:
                            owner = parts[0]
                            session_id = parts[2]
                            upload_id = parts[4] if len(parts) > 4 else parts[-1]
                            if object_store.delete_session_file(owner, session_id, upload_id):
                                logger.info(f"Deleted session file {storage_path} from MinIO")
                                deleted = True
                    elif "/library/" in storage_path:
                        parts = storage_path.split("/")
                        if len(parts) >= 3:
                            owner = parts[0]
                            doc_file_id = parts[-1]
                            if object_store.delete_library_file(owner, doc_file_id):
                                logger.info(f"Deleted library file {storage_path} from MinIO")
                                deleted = True
            except Exception as e:
                logger.warning(f"Failed to delete {storage_path} from MinIO: {e}")
        
        # Step 3: Delete from local filesystem
        if storage_path:
            try:
                # Try to find the file in local upload directory
                from src.constants import UPLOAD_DIR
                # Extract filename from storage_path
                filename = storage_path.split("/")[-1]
                local_path = os.path.join(UPLOAD_DIR, filename)
                
                if os.path.exists(local_path):
                    os.remove(local_path)
                    logger.info(f"Deleted local file {local_path}")
                    deleted = True
            except Exception as e:
                logger.warning(f"Failed to delete local file for {doc_id}: {e}")
        
        # Step 4: Update database record
        try:
            with SessionLocal() as db:
                db_doc = db.query(Document).filter(Document.id == doc_id).first()
                if db_doc:
                    db_doc.file_scope = FileScope.LIBRARY.value
                    db_doc.expires_at = None
                    db_doc.archived = True
                    db.commit()
                    logger.info(f"Marked document {doc_id} as archived")
        except Exception as e:
            logger.error(f"Failed to update database for document {doc_id}: {e}")
        
        return deleted

    def get_stats(self) -> Dict[str, Any]:
        """Get cleanup statistics.
        
        Returns:
            Dictionary with cleanup statistics
        """
        return self._stats.copy()

    def force_expire_session(self, session_id: str, owner: Optional[str] = None) -> Dict[str, Any]:
        """Force expire all documents in a session.
        
        Args:
            session_id: The session ID to expire
            owner: Optional owner filter for multi-tenancy
            
        Returns:
            Dictionary with expiration statistics
        """
        result = {
            "success": True,
            "documents_expired": 0,
            "errors": 0,
        }
        
        try:
            with SessionLocal() as db:
                query = db.query(Document).filter(
                    Document.session_id == session_id,
                    Document.file_scope == FileScope.SESSION.value,
                )
                
                if owner:
                    query = query.filter(Document.owner == owner)
                
                docs = query.all()
                
                for doc in docs:
                    try:
                        doc.expires_at = utcnow()
                        db.commit()
                        result["documents_expired"] += 1
                    except Exception as e:
                        logger.error(f"Failed to expire document {doc.id}: {e}")
                        result["errors"] += 1
                
                logger.info(f"Forced expiration for session {session_id}: {result['documents_expired']} documents")
                return result
                
        except Exception as e:
            logger.error(f"Force expire failed for session {session_id}: {e}")
            result["success"] = False
            result["error"] = str(e)
            return result


# Singleton instance
_cleanup_worker = None


def get_cleanup_worker() -> SessionFileCleanup:
    """Get the singleton cleanup worker instance."""
    global _cleanup_worker
    if _cleanup_worker is None:
        ttl_days = int(os.getenv("SESSION_FILE_TTL_DAYS", "7"))
        _cleanup_worker = SessionFileCleanup(ttl_days=ttl_days)
    return _cleanup_worker


def run_cleanup_job() -> Dict[str, Any]:
    """Run the cleanup job (can be called from task scheduler).
    
    Returns:
        Dictionary with cleanup results
    """
    worker = get_cleanup_worker()
    return worker.cleanup_expired_files()
