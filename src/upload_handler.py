# src/upload_handler.py
import os
import re
import json
import uuid
import time
import hashlib
import mimetypes
import shutil
import tempfile
import threading
from datetime import datetime, timedelta
from core.time_utils import utcnow
from typing import Dict, Any, Optional
from enum import Enum
from fastapi import HTTPException, UploadFile

try:
    from core import feature_flags
    from core.database import SessionLocal, Upload as UploadModel
    from sqlalchemy import func
except Exception:  # pragma: no cover - import-time guard for stripped envs
    feature_flags = None
    SessionLocal = None
    UploadModel = None
    func = None


class FileScope(str, Enum):
    """Scope of a file: session-scoped (temporary) or library (persistent)."""
    SESSION = "session"
    LIBRARY = "library"


def secure_filename(filename: str) -> str:
    """Sanitize a filename (replaces werkzeug.utils.secure_filename)."""
    import unicodedata
    filename = unicodedata.normalize("NFKD", filename)
    filename = filename.encode("ascii", "ignore").decode("ascii")
    # Replace path separators with underscores
    for sep in (os.sep, os.altsep or "", "/", "\\"):
        if sep:
            filename = filename.replace(sep, "_")
    # Keep only safe characters
    filename = re.sub(r"[^\w\s\-.]", "", filename).strip()
    filename = re.sub(r"[\s]+", "_", filename)
    # Don't allow dotfiles
    filename = filename.lstrip(".")
    return filename or "unnamed"
import logging

logger = logging.getLogger(__name__)

# Upload statistics tracking
_upload_stats = {
    "total_uploads": 0,
    "successful_uploads": 0,
    "failed_uploads": 0,
    "duplicate_uploads": 0,
    "total_bytes_uploaded": 0,
    "uploads_by_type": {},
    "uploads_by_scope": {"session": 0, "library": 0},
}


def _log_upload_event(
    event_type: str,
    file_id: str,
    original_filename: str,
    file_size: int,
    content_type: str,
    owner: str = None,
    file_scope: str = "library",
    session_id: str = None,
    error: str = None,
) -> None:
    """Log upload event for auditing and debugging."""
    log_context = f"file_id={file_id} filename={original_filename} size={file_size} mime={content_type}"
    if owner:
        log_context += f" owner={owner}"
    if file_scope:
        log_context += f" scope={file_scope}"
    if session_id:
        log_context += f" session_id={session_id}"
    
    if event_type == "upload_success":
        _upload_stats["total_uploads"] += 1
        _upload_stats["successful_uploads"] += 1
        _upload_stats["total_bytes_uploaded"] += file_size
        _upload_stats["uploads_by_type"][content_type] = _upload_stats["uploads_by_type"].get(content_type, 0) + 1
        _upload_stats["uploads_by_scope"][file_scope] = _upload_stats["uploads_by_scope"].get(file_scope, 0) + 1
        logger.info(f"Upload successful: {log_context}")
    
    elif event_type == "upload_duplicate":
        _upload_stats["total_uploads"] += 1
        _upload_stats["duplicate_uploads"] += 1
        logger.info(f"Upload duplicate detected: {log_context}")
    
    elif event_type == "upload_failed":
        _upload_stats["total_uploads"] += 1
        _upload_stats["failed_uploads"] += 1
        logger.warning(f"Upload failed: {log_context} error={error}")
    
    elif event_type == "download":
        logger.debug(f"File downloaded: {log_context}")
    
    elif event_type == "delete":
        logger.info(f"File deleted: {log_context}")


def get_upload_stats() -> Dict[str, Any]:
    """Get upload statistics."""
    return _upload_stats.copy()

# The extension is optional: save_upload builds the id as `{uuid.hex}{ext}`,
# and a file with no extension (Dockerfile, README, ...) yields a bare 32-hex
# id. Requiring `.ext` made those ids fail validation, so the stored file
# could never be resolved or downloaded again.
UPLOAD_ID_RE = re.compile(r"^[0-9a-fA-F]{32}(?:\.[A-Za-z0-9]+)?$")


def is_valid_upload_id(upload_id: str) -> bool:
    """Return True when *upload_id* matches the canonical uploads.json id format."""
    return UPLOAD_ID_RE.fullmatch(upload_id or "") is not None


def count_recent_uploads(timestamps, now: float, window: float = 10.0) -> int:
    """Number of upload events in *timestamps* within the last *window* seconds.

    Used by the per-IP concurrency guard. The count is of genuine prior upload
    events — it must NOT scale with how many files are in the *current* request,
    or a single multi-file batch would reject itself (issue #1346)."""
    if not timestamps:
        return 0
    cutoff = now - window
    return sum(1 for t in timestamps if t > cutoff)


class UploadHandler:
    def __init__(self, base_dir: str, upload_dir: str, object_store=None):
        self.base_dir = base_dir
        self.upload_dir = upload_dir
        self.object_store = object_store
        self.max_upload_size = 10 * 1024 * 1024  # 10MB
        self.max_concurrent_uploads = 3
        self.cleanup_days = 30
        # Session file TTL in days (default 7 days)
        self.session_file_ttl_days = int(os.getenv("SESSION_FILE_TTL_DAYS", "7"))
        # Per-IP per-minute cap. save_upload() counts EACH file, and the chat
        # composer lets a user attach up to MAX_FILES (10, static/js/fileHandler.js)
        # in one batch — so this must comfortably exceed 10, or a single 6+ file
        # attach is rejected mid-batch (issue #1346: "5 work, 6 fail"). Burst abuse
        # is separately bounded by max_concurrent_uploads. Headroom for a few full
        # batches per minute.
        self.upload_rate_limit = 60  # max 60 file-uploads per minute per IP
        self.upload_rate_window = 60  # 60 seconds

        # Track upload rates
        self.upload_rate_log: Dict[str, list] = {}
        self._upload_rate_lock = threading.Lock()
        self._upload_rate_counter = 0
        self._upload_rate_max_entries = 1000
        # Serialise the read-modify-write of uploads.json within one
        # Python process. Scope: single FastAPI worker (the default
        # uvicorn deployment). Cross-process / multi-worker deployments
        # need an additional file-level lock (flock) or a database;
        # the atomic-rename write below keeps on-disk state consistent
        # on its own but does not serialise writers across processes.
        self._index_lock = threading.Lock()

        # Create upload directory
        os.makedirs(self.upload_dir, exist_ok=True)

        # Initialize file detector
        try:
            import magic
            self.file_detector = magic.Magic(mime=True)
        except Exception:
            self.file_detector = None
            logger.warning("python-magic not available, falling back to basic detection")

    # ── Object-store helpers ─────────────────────────────────────────
    def _minio_enabled(self) -> bool:
        """True when minIO is enabled (env-driven) and the client is healthy."""
        if not self.object_store:
            return False
        # ``enabled`` reflects ODYSSEUS_USE_MINIO at import time. Re-check the
        # env var live so test harnesses that flip it after import still work.
        if os.getenv("ODYSSEUS_USE_MINIO", "false").lower() not in ("1", "true", "yes"):
            return False
        return bool(
            getattr(self.object_store, "enabled", False)
            and getattr(self.object_store, "healthy", False)
        )

    def _minio_required(self) -> bool:
        """True when the operator opted into MinIO, regardless of health.

        Distinct from ``_minio_enabled``: returns True even when the store
        is enabled-but-unreachable. Used to decide whether save_upload
        should fail loudly (env said MinIO) vs fall back to local FS
        (MinIO was never opted in)."""
        if not self.object_store:
            return False
        if not getattr(self.object_store, "enabled", False):
            return False
        return os.getenv("ODYSSEUS_USE_MINIO", "false").lower() in ("1", "true", "yes")

    # ── Upload index storage (DB vs JSON) ───────────────────────────
    def _db_enabled(self) -> bool:
        """True when the upload-metadata index lives in Postgres."""
        return bool(feature_flags and feature_flags.features.infra_enabled("uploads_in_db") and SessionLocal and UploadModel)

    def _dual_write(self) -> bool:
        """True when writes should hit both DB and legacy JSON.
        Read path prefers DB when ``_db_enabled`` is true regardless."""
        return bool(feature_flags and feature_flags.features.infra_enabled("uploads_dual_write"))

    @staticmethod
    def _row_to_dict(row) -> Optional[Dict[str, Any]]:
        if row is None:
            return None
        out: Dict[str, Any] = {
            "id": row.id,
            "path": row.local_path,
            "mime": row.mime,
            "size": row.size,
            "name": row.safe_filename,
            "hash": row.sha256,
            "original_name": row.original_name,
            "owner": row.owner,
            "file_scope": row.file_scope,
            "session_id": row.session_id,
            "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
            "last_accessed": row.last_accessed.isoformat() if row.last_accessed else None,
            "client_ip": row.client_ip,
            "expires_at": row.expires_at.isoformat() if row.expires_at else None,
            "minio_key": row.minio_key,
            "storage_path": row.minio_key,
            "width": row.width,
            "height": row.height,
        }
        return out

    @staticmethod
    def _isolate_dt(value):
        if isinstance(value, datetime):
            return value
        if not value:
            return None
        try:
            return datetime.fromisoformat(str(value).replace("Z", ""))
        except Exception:
            return None

    def _user_object_key(
        self,
        owner: Optional[str],
        file_id: str,
        file_scope: str = "library",
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """Compute the minIO key for an upload and return it.

        Returns None when the object store is disabled or no owner is set.
        
        Key formats (relative to userdata/{owner}/):
        - Session files: sessions/{session_id}/uploads/{file_id}
        - Library files: library/{file_id}
        """
        if not self._minio_enabled() or not owner:
            return None
        
        file_scope = file_scope or "library"
        if file_scope == "session" and session_id:
            return f"sessions/{session_id}/uploads/{file_id}"
        else:
            return f"library/{file_id}"

    def _put_user_object(
        self,
        owner: str,
        key: str,
        data: bytes,
        content_type: str = "application/octet-stream",
    ) -> Optional[str]:
        """Upload to object store, returning the object key (or None)."""
        if not self._minio_enabled():
            return None
        try:
            return self.object_store.put_user_object(owner, key, data, content_type)
        except Exception as exc:
            logger.warning(f"minIO put failed for user={owner} key={key}: {exc}")
            return None

    def _get_user_object(self, owner: str, key: str) -> Optional[bytes]:
        """Download from object store; None on miss or store-down."""
        if not self._minio_enabled():
            return None
        try:
            return self.object_store.get_user_object(owner, key)
        except Exception as exc:
            logger.warning(f"minIO get failed for user={owner} key={key}: {exc}")
            return None
    
    def inside_base_dir(self, path: str) -> bool:
        """Check if path is inside base directory"""
        base = os.path.realpath(self.base_dir)
        p = os.path.realpath(path)
        try:
            return os.path.commonpath([base, p]) == base
        except Exception:
            return False
    
    def get_upload_dir(self):
        """Get date-based upload directory"""
        now = datetime.now()
        upload_dir = os.path.join(self.upload_dir, now.strftime("%Y"), now.strftime("%m"), now.strftime("%d"))
        os.makedirs(upload_dir, exist_ok=True)
        return upload_dir
    
    def calculate_file_hash(self, file_obj) -> str:
        """Calculate SHA-256 hash of file content."""
        file_obj.seek(0)
        hash_sha256 = hashlib.sha256()
        for chunk in iter(lambda: file_obj.read(4096), b""):
            hash_sha256.update(chunk)
        file_obj.seek(0)
        return hash_sha256.hexdigest()
    
    def detect_content_type(self, file_obj, original_filename: str) -> str:
        """Detect MIME type based on file content, with extension fallback."""
        content_type = "application/octet-stream"
        if self.file_detector:
            try:
                file_obj.seek(0)
                content_type = self.file_detector.from_buffer(file_obj.read(1024))
                file_obj.seek(0)
            except Exception as e:
                logger.warning(f"Failed to detect content type: {e}")
        
        if not content_type or content_type == "application/octet-stream":
            _, ext = os.path.splitext(original_filename.lower())
            if ext:
                content_type = mimetypes.guess_type(original_filename)[0] or content_type
        
        return content_type
        
    def is_image_file(self, filename: str, content_type: str = None) -> bool:
        """Check if a file is an image based on extension or content type."""
        image_extensions = {'.png', '.jpg', '.jpeg', '.webp', '.gif'}
        image_mime_types = {
            'image/png', 'image/jpeg', 'image/jpg', 'image/webp', 'image/gif'
        }
        
        # Check by extension
        _, ext = os.path.splitext(filename.lower())
        if ext in image_extensions:
            return True
            
        # Check by content type if provided
        if content_type and content_type in image_mime_types:
            return True
            
        return False
        
    def is_document_file(self, filename: str, content_type: str = None) -> bool:
        """Check if a file is a document based on extension or content type."""
        document_extensions = {
            '.pdf', '.docx', '.xlsx', '.pptx', '.xls', '.epub',
            '.txt', '.py', '.js', '.html', '.htm',
            '.css', '.json', '.md', '.csv', '.log', '.xml', '.yml', 
            '.yaml', '.sql', '.sh', '.bash', '.c', '.cpp', '.h', 
            '.java', '.go', '.rs', '.php', '.rb', '.ts', '.jsx', '.tsx'
        }
        document_mime_types = {
            'application/pdf', 
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            'application/vnd.ms-excel',
            'application/epub+zip',
            'text/plain'
        }
        
        # Check by extension
        _, ext = os.path.splitext(filename.lower())
        if ext in document_extensions:
            return True
            
        # Check by content type if provided
        if content_type and content_type in document_mime_types:
            return True
            
        return False
            
    def is_audio_file(self, filename: str, content_type: str = None) -> bool:
        """Check if a file is an audio file based on extension or content type."""
        audio_extensions = {'.webm', '.wav', '.mp3', '.m4a', '.ogg'}
        audio_mime_types = {
            'audio/webm', 'audio/wav', 'audio/mpeg', 'audio/mp4', 'audio/ogg'
        }
        
        # Check by extension
        _, ext = os.path.splitext(filename.lower())
        if ext in audio_extensions:
            return True
            
        # Check by content type if provided
        if content_type and content_type in audio_mime_types:
            return True
            
        return False
    
    def is_safe_file_type(self, content_type: str, filename: str) -> bool:
        """Check if file type is safe to store and serve."""
        dangerous_types = {
            'application/x-executable', 'application/x-sharedlib',
            'application/x-dll', 'application/x-msdownload',
            'application/x-sh', 'application/x-bat', 'application/x-vbs',
            'application/javascript', 'application/x-javascript'
        }
        
        dangerous_extensions = {
            '.exe', '.dll', '.bat', '.cmd', '.vbs', 
            '.ps1', '.jsp', '.asp', '.aspx'
        }
        
        if content_type in dangerous_types:
            return False
        
        _, ext = os.path.splitext(filename.lower())
        if ext in dangerous_extensions:
            return False
        
        return True
    
    def cleanup_old_uploads(self):
        """Remove uploaded files older than CLEANUP_DAYS days."""
        try:
            cutoff_date = datetime.now() - timedelta(days=self.cleanup_days)
            cleaned_count = 0
            
            for root, dirs, files in os.walk(self.upload_dir):
                if root == self.upload_dir:
                    continue
                    
                path_parts = root.split(os.sep)
                if len(path_parts) >= 4:
                    try:
                        dir_date = datetime(int(path_parts[-3]), int(path_parts[-2]), int(path_parts[-1]))
                        if dir_date < cutoff_date:
                            for file in files:
                                file_path = os.path.join(root, file)
                                try:
                                    os.remove(file_path)
                                    cleaned_count += 1
                                    logger.info(f"Cleaned up old upload: {file_path}")
                                except Exception as e:
                                    logger.warning(f"Failed to remove {file_path}: {e}")
                            
                            try:
                                os.rmdir(root)
                                logger.info(f"Removed empty upload directory: {root}")
                            except Exception as e:
                                logger.warning(f"Failed to remove directory {root}: {e}")
                    except (ValueError, IndexError):
                        continue
            
            logger.info(f"Upload cleanup completed: {cleaned_count} files removed")
            return cleaned_count
        except Exception as e:
            logger.error(f"Upload cleanup failed: {e}")
            return 0
    
    def validate_upload_id(self, upload_id: str) -> bool:
        """Validate that the upload ID matches the expected pattern."""
        return is_valid_upload_id(upload_id)

    def _inside_upload_dir(self, path: str) -> bool:
        """Check if path is inside the upload directory."""
        base = os.path.realpath(self.upload_dir)
        p = os.path.realpath(path)
        try:
            return os.path.commonpath([base, p]) == base
        except Exception:
            return False

    def _atomic_write_json(self, path: str, data: dict) -> None:
        """Write `data` to `path` atomically: write to a temp file in the
        same directory, then `os.replace` onto the target. The kernel
        guarantees `os.replace` is atomic on POSIX, so a reader either
        sees the old contents or the new contents, never a half-written
        file. Also keeps a `.bak` sibling of the previous good state.
        """
        directory = os.path.dirname(path) or "."
        fd, tmp = tempfile.mkstemp(prefix=".uploads-", suffix=".tmp", dir=directory)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            if os.path.exists(path):
                bak = path + ".bak"
                try:
                    shutil.copy2(path, bak)
                except OSError:
                    pass
            os.replace(tmp, path)
        except Exception:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise

    def _load_upload_index(self) -> Dict[str, Any]:
        uploads_db_path = os.path.join(self.upload_dir, "uploads.json")
        if not os.path.exists(uploads_db_path):
            return {}
        # Try the live file first, fall back to the .bak sibling if the
        # live file is truncated/corrupted (e.g. a previous writer was
        # SIGKILL'd mid-rename before the new code path was deployed).
        for candidate in (uploads_db_path, uploads_db_path + ".bak"):
            if not os.path.exists(candidate):
                continue
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return data if isinstance(data, dict) else {}
            except Exception as e:
                logger.warning(f"Failed to read uploads database ({candidate}): {e}")
                continue
        return {}

    def get_upload_info(self, upload_id: str) -> Optional[Dict[str, Any]]:
        """Return the metadata row for an upload ID, if present.

        Prefers the DB when ``uploads_in_db`` is on; falls back to the
        legacy JSON index otherwise.
        """
        if not self.validate_upload_id(upload_id):
            return None
        if self._db_enabled():
            try:
                with SessionLocal() as db:
                    row = db.query(UploadModel).filter(UploadModel.id == upload_id).first()
                    if row:
                        return self._row_to_dict(row)
            except Exception as e:
                logger.warning(f"DB get_upload_info failed ({upload_id}): {e}; falling back to JSON")
        for info in self._load_upload_index().values():
            if isinstance(info, dict) and info.get("id") == upload_id:
                return dict(info)
        return None

    def _find_upload_path(self, upload_id: str) -> Optional[str]:
        """Find an upload file by ID while staying inside upload_dir."""
        if not self.validate_upload_id(upload_id):
            return None

        direct = os.path.join(self.upload_dir, upload_id)
        if os.path.exists(direct) and self._inside_upload_dir(direct):
            return direct

        for root, _dirs, files in os.walk(self.upload_dir, followlinks=False):
            if upload_id in files:
                path = os.path.join(root, upload_id)
                if self._inside_upload_dir(path):
                    return path
        return None

    def resolve_upload(
        self,
        upload_id: str,
        owner: Optional[str] = None,
        auth_manager: Any = None,
        allow_admin: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Resolve an upload ID to metadata only if the caller may read it.

        This is the owner-aware lookup used by internal processors. Public
        download routes already perform owner checks; chat/document paths must
        do the same before reading file bytes server-side.
        """
        if not self.validate_upload_id(upload_id):
            logger.warning(f"Invalid upload ID format: {upload_id}")
            return None

        auth_configured = bool(auth_manager and getattr(auth_manager, "is_configured", False))
        if auth_configured and not owner:
            return None

        info = self.get_upload_info(upload_id) or {}
        is_admin = False
        if allow_admin and owner and auth_manager and hasattr(auth_manager, "is_admin"):
            try:
                is_admin = bool(auth_manager.is_admin(owner))
            except Exception:
                is_admin = False

        if owner and not is_admin:
            if info.get("owner") != owner:
                logger.warning("Upload %s denied for owner %s", upload_id, owner)
                return None
        if not owner and info.get("owner") is not None:
            logger.warning("Upload %s denied without an authenticated owner", upload_id)
            return None

        path = info.get("path")
        if not path or not os.path.exists(path) or not self._inside_upload_dir(path):
            path = self._find_upload_path(upload_id)
        if not path:
            return None
        if not self._inside_upload_dir(path):
            logger.warning(f"Upload path outside upload directory: {path}")
            return None

        resolved = dict(info)
        resolved.setdefault("id", upload_id)
        resolved["path"] = path
        resolved.setdefault("name", os.path.basename(path))
        resolved.setdefault("original_name", resolved["name"])
        resolved.setdefault("mime", mimetypes.guess_type(path)[0] or "application/octet-stream")
        return resolved

    def fetch_from_minio(
        self,
        upload_id: str,
        owner: Optional[str] = None,
    ) -> Optional[str]:
        """Fetch an upload from MinIO into the local upload dir.

        Returns the local path on success, None if MinIO is disabled,
        the upload is missing in MinIO, or owner is not set.
        """
        if not self.validate_upload_id(upload_id):
            return None
        if not self._minio_enabled() or not owner:
            return None

        info = self.get_upload_info(upload_id) or {}
        minio_key = info.get("minio_key") or info.get("storage_path")
        if not minio_key:
            return None

        try:
            data = self.object_store.get_user_object(owner, minio_key)
        except Exception as exc:
            logger.warning(
                "fetch_from_minio: get_user_object failed for owner=%s key=%s: %s",
                owner, minio_key, exc,
            )
            return None

        if not data:
            return None

        # Resolve a safe local path under upload_dir
        local_name = secure_filename(info.get("original_name") or info.get("name") or upload_id)
        local_path = os.path.join(self.upload_dir, local_name)
        # Avoid collisions
        base, ext = os.path.splitext(local_path)
        counter = 1
        while os.path.exists(local_path):
            local_path = f"{base}_{counter}{ext}"
            counter += 1

        try:
            with open(local_path, "wb") as f:
                f.write(data)
            logger.info(
                "fetch_from_minio: restored owner=%s key=%s -> %s",
                owner, minio_key, local_path,
            )
        except Exception as exc:
            logger.warning(
                "fetch_from_minio: local write failed for owner=%s key=%s: %s",
                owner, minio_key, exc,
            )
            return None

        return local_path

    def resolve_upload_with_fetch(
        self,
        upload_id: str,
        owner: Optional[str] = None,
        auth_manager: Any = None,
        allow_admin: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Like resolve_upload, but transparently fetches from MinIO on cache miss."""
        resolved = self.resolve_upload(
            upload_id,
            owner=owner,
            auth_manager=auth_manager,
            allow_admin=allow_admin,
        )
        if resolved and resolved.get("path") and os.path.exists(resolved["path"]):
            return resolved

        # Cache miss — try MinIO
        fetched_path = self.fetch_from_minio(upload_id, owner=owner)
        if not fetched_path:
            logger.warning(
                "resolve_upload_with_fetch: upload %s not retrievable "
                "(local miss + minIO miss)",
                upload_id,
            )
            return None

        # Re-resolve now that the file is local
        return self.resolve_upload(
            upload_id,
            owner=owner,
            auth_manager=auth_manager,
            allow_admin=allow_admin,
        )
    
    def cleanup_rate_limits(self):
        """Remove stale entries from upload_rate_log."""
        now = time.time()
        removed_ips = 0
        removed_timestamps = 0
        
        with self._upload_rate_lock:
            ips_to_delete = []
            for ip, timestamps in list(self.upload_rate_log.items()):
                new_ts = [t for t in timestamps if now - t < self.upload_rate_window]
                removed = len(timestamps) - len(new_ts)
                removed_timestamps += removed
                if new_ts:
                    self.upload_rate_log[ip] = new_ts
                else:
                    ips_to_delete.append(ip)
            
            for ip in ips_to_delete:
                del self.upload_rate_log[ip]
                removed_ips += 1
            
            if len(self.upload_rate_log) > self._upload_rate_max_entries:
                sorted_ips = sorted(
                    self.upload_rate_log.items(),
                    key=lambda item: max(item[1]) if item[1] else 0,
                    reverse=True
                )
                keep = dict(sorted_ips[:self._upload_rate_max_entries])
                dropped = len(self.upload_rate_log) - len(keep)
                self.upload_rate_log = keep
                logger.info(f"Rate-limit dict size exceeded. Dropped {dropped} oldest IP entries.")
        
        logger.info(f"Rate-limit cleanup: removed {removed_ips} IPs, {removed_timestamps} timestamps.")
    
    def get_upload_stats(self) -> Dict[str, Any]:
        """Get statistics about uploaded files."""
        try:
            total_files = 0
            total_size = 0
            file_types = {}

            if self._db_enabled():
                try:
                    with SessionLocal() as db:
                        total_files = db.query(UploadModel).count() or 0
                        size_sum = db.query(func.sum(UploadModel.size)).scalar() if False else None
                        # func.sum may return Decimal on PG; cast defensively.
                        try:
                            from sqlalchemy import func as _f
                            size_sum = db.query(_f.sum(UploadModel.size)).scalar()
                        except Exception:
                            size_sum = None
                        total_size = int(size_sum or 0)
                        for mime, cnt in (
                            db.query(UploadModel.mime, func.count(UploadModel.id))
                            .group_by(UploadModel.mime)
                            .all()
                        ):
                            file_types[mime or "unknown"] = int(cnt)
                except Exception as e:
                    logger.warning(f"DB stats query failed: {e}; falling back to JSON")

            if not total_files and not file_types:
                uploads_db_path = os.path.join(self.upload_dir, "uploads.json")
                if os.path.exists(uploads_db_path):
                    with open(uploads_db_path, "r", encoding="utf-8") as f:
                        files = json.load(f)

                    total_files = len(files)
                    for file_info in files.values():
                        total_size += file_info.get("size", 0)
                        mime = file_info.get("mime", "unknown")
                        file_types[mime] = file_types.get(mime, 0) + 1

            return {
                "total_files": total_files,
                "total_size": total_size,
                "total_size_mb": round(total_size / (1024 * 1024), 2),
                "file_types": file_types,
                "cleanup_days": self.cleanup_days
            }
        except Exception as e:
            logger.error(f"Failed to get upload stats: {e}")
            return {"error": str(e)}
    
    def save_upload(
        self,
        u: UploadFile,
        client_ip: str,
        owner: str = None,
        file_scope: str = "library",
        session_id: str = None,
        expires_at: datetime = None,
    ) -> dict:
        """Save uploaded file with enhanced security and organization.
        
        Args:
            u: The uploaded file
            client_ip: Client IP for rate limiting
            owner: Owner username for multi-tenancy
            file_scope: "session" for temporary files, "library" for persistent
            session_id: Required for session-scoped files
            expires_at: Expiration timestamp (auto-computed for session files)
        """
        # Rate limiting
        now = time.time()
        with self._upload_rate_lock:
            if client_ip not in self.upload_rate_log:
                self.upload_rate_log[client_ip] = []
            
            self.upload_rate_log[client_ip] = [
                timestamp for timestamp in self.upload_rate_log[client_ip]
                if now - timestamp < self.upload_rate_window
            ]
            
            if len(self.upload_rate_log[client_ip]) >= self.upload_rate_limit:
                raise HTTPException(
                    status_code=429,
                    detail="Upload rate limit exceeded. Please try again later."
                )
            
            self.upload_rate_log[client_ip].append(now)
            self._upload_rate_counter += 1
        
        if self._upload_rate_counter % 100 == 0:
            self.cleanup_rate_limits()
        
        # Get original filename early for error logging
        original_filename = u.filename or f"upload_{int(time.time())}"
        safe_filename = secure_filename(original_filename)
        
        # Validate file size
        file_obj = u.file
        file_obj.seek(0, 2)
        file_size = file_obj.tell()
        file_obj.seek(0)
        
        if file_size == 0:
            _log_upload_event("upload_failed", "unknown", original_filename, 0, "unknown", owner, file_scope, session_id, "File is empty")
            raise HTTPException(400, "File is empty")
            
        if file_size > self.max_upload_size:
            _log_upload_event("upload_failed", "unknown", original_filename, file_size, "unknown", owner, file_scope, session_id, f"File size exceeds {self.max_upload_size/1024/1024}MB limit")
            raise HTTPException(
                status_code=400,
                detail=f"File size exceeds {self.max_upload_size/1024/1024}MB limit"
            )
        
        # Detect content type
        content_type = self.detect_content_type(file_obj, safe_filename)
        
        # Check if file type is safe
        if not self.is_safe_file_type(content_type, safe_filename):
            _log_upload_event("upload_failed", "unknown", original_filename, file_size, content_type, owner, file_scope, session_id, f"File type not allowed: {content_type}")
            raise HTTPException(
                status_code=400,
                detail=f"File type not allowed: {content_type}"
            )
        
        # Calculate file hash for deduplication
        file_hash = self.calculate_file_hash(file_obj)
        
        # Check for duplicate files.
        # ``owner is None`` represents a pre-auth / unauthenticated upload
        # context. The DB dedup constraint is ``(owner, sha256)``; treating
        # None as ``""`` keeps the lookup consistent across rows stored
        # before and after the DB cutover.
        uploads_db_path = os.path.join(self.upload_dir, "uploads.json")
        owner_for_dedupe = owner if owner is not None else ""

        if self._db_enabled():
            try:
                with SessionLocal() as db:
                    row = (
                        db.query(UploadModel)
                        .filter(UploadModel.owner == owner_for_dedupe)
                        .filter(UploadModel.sha256 == file_hash)
                        .first()
                    )
                    if row:
                        stored_path = row.local_path
                        if stored_path and os.path.exists(stored_path) and self._inside_upload_dir(stored_path):
                            row.last_accessed = utcnow()
                            db.commit()
                            existing_file = self._row_to_dict(row)
                            _log_upload_event(
                                "upload_duplicate",
                                row.id,
                                original_filename,
                                file_size,
                                content_type,
                                owner,
                                file_scope,
                                session_id,
                            )
                            logger.info(
                                "save_upload: DUPLICATE detected — skipping upload. "
                                "filename=%s owner=%s existing_id=%s",
                                original_filename, owner, row.id,
                            )
                            existing_file["is_duplicate"] = True
                            return existing_file
                        logger.info(
                            "save_upload: dedup row found but file missing — re-uploading. id=%s",
                            row.id,
                        )
            except Exception as e:
                logger.warning(f"DB dedup lookup failed: {e}; falling back to JSON index")

        # Legacy JSON dedup path.
        existing_file = None
        existing_key = None
        with self._index_lock:
            existing_files = self._load_upload_index()
            stale_keys = []
            for key, info in existing_files.items():
                if info.get("hash") == file_hash and info.get("owner") == owner:
                    stored_path = info.get("path")
                    if stored_path and os.path.exists(stored_path) and self._inside_upload_dir(stored_path):
                        existing_key = key
                        existing_file = info
                        break
                    stale_keys.append(key)
            if stale_keys:
                for key in stale_keys:
                    existing_files.pop(key, None)
                try:
                    self._atomic_write_json(uploads_db_path, existing_files)
                    logger.info("Removed %d stale upload index entries for missing duplicates", len(stale_keys))
                except Exception as e:
                    logger.warning(f"Failed to remove stale upload index entries: {e}")
        if existing_file:
            _log_upload_event(
                "upload_duplicate",
                existing_file.get("id", file_id),
                original_filename,
                file_size,
                content_type,
                owner,
                file_scope,
                session_id,
            )
            logger.info(
                "save_upload: DUPLICATE detected — skipping upload. "
                "filename=%s owner=%s existing_id=%s",
                original_filename, owner, existing_file.get("id"),
            )

            existing_file["last_accessed"] = datetime.now().isoformat()
            with self._index_lock:
                try:
                    current = self._load_upload_index()
                    # Re-resolve the key inside the lock: a concurrent
                    # insert can have changed the dict's keys.
                    live_key = existing_key
                    if live_key not in current:
                        for k, v in current.items():
                            if v.get("hash") == file_hash and v.get("owner") == owner:
                                live_key = k
                                existing_file = v
                                break
                    if live_key is None:
                        # No matching entry anymore (e.g. cleaned up between
                        # the outer read and the write). Fall through to the
                        # fresh-insert path below; release the lock first.
                        raise LookupError("upload entry vanished mid-dedupe")
                    existing_file["last_accessed"] = datetime.now().isoformat()
                    current[live_key] = existing_file
                    self._atomic_write_json(uploads_db_path, current)
                except LookupError:
                    existing_file = None
                except Exception as e:
                    logger.warning(f"Failed to update uploads database: {e}")

            if existing_file:
                return {
                    "id": existing_file["id"],
                    "path": existing_file["path"],
                    "mime": existing_file["mime"],
                    "size": existing_file["size"],
                    "name": existing_file["original_name"],
                    "hash": file_hash,
                    "uploaded_at": existing_file["uploaded_at"],
                    "owner": existing_file.get("owner"),
                    "width": existing_file.get("width"),
                    "height": existing_file.get("height"),
                    "is_duplicate": True
                }

        # Generate unique ID preserving original filename with timestamp for uniqueness
        _, ext = os.path.splitext(safe_filename)
        name_without_ext = os.path.splitext(safe_filename)[0]
        timestamp = int(time.time() * 1000)
        file_id = f"{name_without_ext}_{timestamp}{ext}"

        # Create date-based directory structure
        upload_dir = self.get_upload_dir()
        file_path = os.path.join(upload_dir, file_id)

        # Read the entire upload into memory once so we can write to local FS
        # and minIO without re-streaming. Cap at max_upload_size (10MB), so
        # this is bounded.
        file_bytes = file_obj.read()
        logger.info(
            "save_upload: filename=%s owner=%s size=%s bytes minio_enabled=%s",
            original_filename, owner, len(file_bytes), self._minio_enabled(),
        )

        # Operator intent is one of two states — and they must behave
        # differently on failure:
        #   * opted-in (ODYSSEUS_USE_MINIO=true): MinIO is the source of
        #     truth. If it is unreachable at runtime, that is an operational
        #     failure the user must see — silent fallback to local FS hides
        #     broken deployments and silently drops uploads.
        #   * opted-out: local FS is the configured primary; MinIO is never
        #     touched.
        required = self._minio_required()
        enabled = self._minio_enabled()
        minio_key = None

        if required and not enabled:
            logger.error(
                "save_upload: MinIO is required (ODYSSEUS_USE_MINIO=true) but "
                "unreachable — rejecting upload owner=%s file=%s",
                owner, original_filename,
            )
            raise HTTPException(
                status_code=503,
                detail=(
                    "Object storage is required but unreachable. The file was NOT "
                    "saved. Check MinIO connectivity (endpoint in startup logs) "
                    "and retry."
                ),
            )

        if not required:
            logger.info(
                "save_upload: MinIO not opted in — storing on local FS only (owner=%s)",
                owner,
            )

        # required and enabled — proceed with MinIO as source of truth.
        if required:
            minio_key = self._user_object_key(owner, file_id, file_scope, session_id)
            logger.info(
                "save_upload: computed minio_key=%s (owner=%s file_id=%s scope=%s session=%s)",
                minio_key, owner, file_id, file_scope, session_id,
            )
            try:
                full_key = self.object_store.put_user_object(
                    owner, minio_key, file_bytes, content_type
                )
                logger.info(
                    "save_upload: STORED IN MINIO owner=%s file_id=%s key=%s full_key=%s size=%s",
                    owner, file_id, minio_key, full_key, len(file_bytes),
                )
                logger.info(
                    "NEW DOCUMENT: owner=%s filename=%s scope=%s size=%s "
                    "minio_key=%s session_id=%s content_type=%s",
                    owner, original_filename, file_scope, len(file_bytes),
                    minio_key, session_id, content_type,
                )
                # Source of truth is now MinIO — remove any staged local copy.
                if os.path.exists(file_path):
                    try:
                        os.remove(file_path)
                        logger.info("save_upload: removed local copy %s", file_path)
                    except Exception as e:
                        logger.warning(
                            "save_upload: failed to remove local copy %s: %s", file_path, e
                        )
            except Exception as exc:
                logger.error(
                    "save_upload: minIO put FAILED for owner=%s file=%s key=%s: %s — rejecting",
                    owner, file_id, minio_key, exc,
                )
                raise HTTPException(
                    status_code=503,
                    detail=(
                        f"Object storage write failed: {exc}. The file was NOT saved."
                    ),
                )

        # Local-FS write — only when the operator never opted into MinIO.
        if not required:
            try:
                with open(file_path, "wb") as f:
                    f.write(file_bytes)
                logger.info(
                    "NEW DOCUMENT (LOCAL FS): owner=%s filename=%s scope=%s size=%s "
                    "local_path=%s",
                    owner, original_filename, file_scope, len(file_bytes), file_path,
                )
            except Exception as e:
                logger.error("save_upload: local write failed: %s", e)
                raise HTTPException(
                    status_code=500, detail=f"Failed to save file: {str(e)}"
                )

        # Create file metadata
        file_metadata = {
            "id": file_id,
            "path": file_path,
            "mime": content_type,
            "size": file_size,
            "name": safe_filename,
            "hash": file_hash,
            "original_name": original_filename,
            "uploaded_at": datetime.now().isoformat(),
            "last_accessed": datetime.now().isoformat(),
            "client_ip": client_ip,
            "owner": owner,
            "file_scope": file_scope,
            "session_id": session_id,
            "expires_at": expires_at.isoformat() if expires_at else None,
        }
        if minio_key:
            file_metadata["minio_key"] = minio_key
            file_metadata["storage_path"] = minio_key
        # Capture image dimensions (EXIF-rotated) so the chat thumbnail skeleton
        # can size itself to the right aspect ratio before the bytes arrive.
        if content_type.startswith("image/"):
            try:
                from PIL import Image, ImageOps
                with Image.open(file_path) as _im:
                    _im = ImageOps.exif_transpose(_im)
                    file_metadata["width"] = _im.width
                    file_metadata["height"] = _im.height
            except Exception as e:
                logger.warning(f"Failed to read image dimensions for {file_id}: {e}")
        
        # Update uploads database. Under ``uploads_in_db`` the DB row is
        # the canonical record; ``uploads_dual_write`` keeps the legacy
        # JSON index alive in parallel for rollback.
        wrote_db = False
        if self._db_enabled():
            try:
                with SessionLocal() as db:
                    row = UploadModel(
                        id=file_id,
                        owner=owner_for_dedupe,
                        file_scope=file_scope or "library",
                        session_id=session_id,
                        original_name=original_filename,
                        safe_filename=safe_filename,
                        mime=content_type,
                        size=file_size,
                        sha256=file_hash,
                        client_ip=client_ip,
                        uploaded_at=utcnow(),
                        last_accessed=utcnow(),
                        expires_at=self._isolate_dt(expires_at.isoformat() if expires_at else None),
                        minio_key=minio_key,
                        local_path=file_path,
                        width=file_metadata.get("width"),
                        height=file_metadata.get("height"),
                    )
                    db.add(row)
                    db.commit()
                    wrote_db = True
            except Exception as e:
                logger.warning(f"DB insert failed for upload {file_id}: {e}")
                # If DB-only and the insert failed, we have no metadata
                # record — surface so the caller doesn't silently lose
                # the upload id.
                if not self._dual_write():
                    raise HTTPException(status_code=500, detail="Failed to persist upload metadata")

        if not wrote_db or self._dual_write():
            with self._index_lock:
                try:
                    current = self._load_upload_index() if os.path.exists(uploads_db_path) else {}
                    storage_key = f"{owner}:{file_hash}" if owner else file_hash
                    current[storage_key] = file_metadata
                    self._atomic_write_json(uploads_db_path, current)
                except Exception as e:
                    logger.warning(f"Failed to update uploads database: {e}")
        
        _log_upload_event(
            "upload_success",
            file_id,
            original_filename,
            file_size,
            content_type,
            owner,
            file_scope,
            session_id,
        )
        logger.info(f"File uploaded successfully: {original_filename} ({file_size} bytes)")
        return file_metadata
