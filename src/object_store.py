"""src/object_store.py

Per-user object storage (minIO/S3) for uploaded files, embeddings, and
other user-scoped data. All objects are namespaced under a per-user
prefix so that one tenant's data is segregated from another's.

Connection is configured via environment variables::

    MINIO_ENDPOINT   default: localhost:9000  (host:port, no scheme)
    MINIO_ACCESS_KEY default: minioadmin
    MINIO_SECRET_KEY default: minioadmin
    MINIO_BUCKET     default: ody-userdata
    MINIO_SECURE     default: false           (https vs http)
    MINIO_REGION     default: us-east-1

Set ``ODYSSEUS_USE_MINIO=true`` to enable. When disabled, callers should
fall back to local filesystem paths (the legacy behaviour).
"""

from __future__ import annotations

import logging
import os
from typing import Iterator, Optional

logger = logging.getLogger(__name__)

# Master switch — when false, callers should use local FS instead.
USE_MINIO: bool = os.getenv("ODYSSEUS_USE_MINIO", "false").lower() in (
    "1",
    "true",
    "yes",
)

_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")
_BUCKET = os.getenv("MINIO_BUCKET", "ody-userdata")
_SECURE: bool = os.getenv("MINIO_SECURE", "false").lower() in (
    "1",
    "true",
    "yes",
)
_REGION = os.getenv("MINIO_REGION", "us-east-1")


def _user_prefix(user_id: str) -> str:
    """Top-level per-user prefix (no trailing slash)."""
    return f"userdata/{user_id}"


def _session_file_path(session_id: str, upload_id: str) -> str:
    """Path for session-scoped temporary files (relative to userdata/{owner}/).
    
    Format: sessions/{session_id}/uploads/{upload_id}
    """
    return f"sessions/{session_id}/uploads/{upload_id}"


def _library_file_path(doc_id: str) -> str:
    """Path for persistent library documents (relative to userdata/{owner}/).

    Format: library/{doc_id}
    """
    return f"library/{doc_id}"


def _brain_file_path(brain_name: str) -> str:
    """Path for per-user "core brain" config files (relative to userdata/{owner}/).

    Format: brains/{brain_name}
    """
    return f"brains/{brain_name}"


class ObjectStore:
    """Thin wrapper around a minIO/S3 client.

    Lazily creates the bucket on first use. Exposes a ``healthy`` flag
    so callers can decide whether to fall back to local FS.
    """

    def __init__(self) -> None:
        self._client = None
        self._healthy = False
        self._enabled = USE_MINIO

        logger.info(
            "ObjectStore init: USE_MINIO=%s endpoint=%s bucket=%s secure=%s region=%s "
            "access_key_len=%s secret_key_len=%s",
            USE_MINIO,
            _ENDPOINT,
            _BUCKET,
            _SECURE,
            _REGION,
            len(_ACCESS_KEY or ""),
            len(_SECRET_KEY or ""),
        )

        if not self._enabled:
            logger.info("ODYSSEUS_USE_MINIO=false — object store disabled, using local FS")
            return

        try:
            from minio import Minio
        except ImportError as exc:
            logger.warning(
                "minio package not available (%s) — object store disabled. "
                "Run `pip install minio` to enable.",
                exc,
            )
            self._enabled = False
            return

        try:
            self._client = Minio(
                endpoint=_ENDPOINT,
                access_key=_ACCESS_KEY,
                secret_key=_SECRET_KEY,
                secure=_SECURE,
                region=_REGION,
            )
            # Create bucket if missing
            bucket_exists = self._client.bucket_exists(_BUCKET)
            logger.info(
                "minIO bucket_exists(%s) = %s",
                _BUCKET, bucket_exists,
            )
            if not bucket_exists:
                self._client.make_bucket(_BUCKET)
                logger.info("Created minIO bucket: %s", _BUCKET)
            self._healthy = True
            logger.info(
                "minIO object store healthy: endpoint=%s bucket=%s secure=%s",
                _ENDPOINT,
                _BUCKET,
                _SECURE,
            )
        except Exception as exc:
            logger.warning(
                "minIO object store unreachable (%s) — uploads will fall back to local FS",
                exc,
            )
            self._client = None
            self._healthy = False

    # ── Properties ───────────────────────────────────────────────────

    @property
    def enabled(self) -> bool:
        """True when ODYSSEUS_USE_MINIO=true was set at import time."""
        return self._enabled

    @property
    def healthy(self) -> bool:
        """True when enabled AND the minIO client connected successfully."""
        return self._enabled and self._healthy and self._client is not None

    # ── Helpers ──────────────────────────────────────────────────────

    @staticmethod
    def user_prefix(user_id: str) -> str:
        """Top-level per-user prefix (no trailing slash)."""
        return _user_prefix(user_id)

    @staticmethod
    def session_file_path(session_id: str, upload_id: str) -> str:
        """Compute path for session-scoped temporary files (relative to userdata/{owner}/).
        
        Returns: sessions/{session_id}/uploads/{upload_id}
        """
        return _session_file_path(session_id, upload_id)

    @staticmethod
    def library_file_path(doc_id: str) -> str:
        """Compute path for persistent library documents (relative to userdata/{owner}/).
        
        Returns: library/{doc_id}
        """
        return _library_file_path(doc_id)

    def _full_key(self, user_id: str, key: str) -> str:
        """Join user prefix and key into the full minIO object key."""
        return f"{_user_prefix(user_id)}/{key.lstrip('/')}"

    # ── Object operations ────────────────────────────────────────────

    def put_user_object(
        self,
        user_id: str,
        key: str,
        data: bytes | bytearray | str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload ``data`` under ``userdata/{user_id}/{key}``.

        Returns the full object key written. Raises ``RuntimeError`` if
        the store is not healthy (caller should fall back).
        """
        logger.info(
            "put_user_object: user_id=%s key=%s size=%s ct=%s",
            user_id, key, len(data) if hasattr(data, "__len__") else "?", content_type,
        )
        if not self.healthy:
            logger.warning("put_user_object: store not healthy — falling back")
            raise RuntimeError("object store not healthy")

        if isinstance(data, str):
            data = data.encode("utf-8")

        full_key = self._full_key(user_id, key)
        import io

        stream = io.BytesIO(data)
        try:
            self._client.put_object(
                bucket_name=_BUCKET,
                object_name=full_key,
                data=stream,
                length=len(data),
                content_type=content_type,
            )
            logger.info(
                "put_user_object: SUCCESS — bucket=%s key=%s size=%s",
                _BUCKET, full_key, len(data),
            )
            return full_key
        except Exception as exc:
            logger.error(
                "put_user_object: FAILED — bucket=%s key=%s error=%s",
                _BUCKET, full_key, exc,
            )
            raise

    def get_user_object(self, user_id: str, key: str) -> Optional[bytes]:
        """Download ``userdata/{user_id}/{key}`` as bytes.

        Returns None if the object does not exist or the store is down.
        """
        if not self.healthy:
            return None

        from minio.error import S3Error

        full_key = self._full_key(user_id, key)
        try:
            response = self._client.get_object(_BUCKET, full_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            if "NoSuchKey" in str(exc):
                return None
            logger.error("get_object failed for %s: %s", full_key, exc)
            return None
        except Exception as exc:
            logger.error("get_object failed for %s: %s", full_key, exc)
            return None

    def stat_user_object(self, user_id: str, key: str) -> Optional[dict]:
        """Return object metadata if it exists, else None."""
        if not self.healthy:
            return None

        from minio.error import S3Error

        full_key = self._full_key(user_id, key)
        try:
            stat = self._client.stat_object(_BUCKET, full_key)
            return {
                "key": full_key,
                "size": stat.size,
                "etag": stat.etag,
                "content_type": stat.content_type,
                "last_modified": stat.last_modified,
            }
        except S3Error:
            return None
        except Exception:
            return None

    def delete_user_object(self, user_id: str, key: str) -> bool:
        """Delete ``userdata/{user_id}/{key}``. Returns True on success."""
        if not self.healthy:
            return False

        from minio.error import S3Error

        full_key = self._full_key(user_id, key)
        try:
            self._client.remove_object(_BUCKET, full_key)
            return True
        except S3Error as exc:
            logger.error("remove_object failed for %s: %s", full_key, exc)
            return False

    def list_user_objects(
        self,
        user_id: str,
        prefix: str = "",
        recursive: bool = True,
    ) -> Iterator[str]:
        """Yield object keys under ``userdata/{user_id}/{prefix}``.

        When the store is not healthy, yields nothing.
        """
        if not self.healthy:
            return iter(())

        full_prefix = self._full_key(user_id, prefix)
        try:
            for obj in self._client.list_objects(
                _BUCKET, prefix=full_prefix, recursive=recursive
            ):
                yield obj.object_name
        except Exception as exc:
            logger.error("list_objects failed for %s: %s", full_prefix, exc)
            return iter(())

    # ── Session file operations ──────────────────────────────────────

    def put_session_file(
        self,
        owner: str,
        session_id: str,
        upload_id: str,
        data: bytes | bytearray | str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a session-scoped temporary file.
        
        Path: userdata/{owner}/sessions/{session_id}/uploads/{upload_id}
        Returns the full object key written.
        """
        key = self.session_file_path(session_id, upload_id)
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        full_key = self._full_key(owner, key)
        import io
        stream = io.BytesIO(data)
        
        self._client.put_object(
            bucket_name=_BUCKET,
            object_name=full_key,
            data=stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info("put_session_file: SUCCESS owner=%s session=%s upload=%s", owner, session_id, upload_id)
        return full_key

    def get_session_file(
        self,
        owner: str,
        session_id: str,
        upload_id: str,
    ) -> Optional[bytes]:
        """Download a session-scoped file. Returns None if not found."""
        key = self.session_file_path(session_id, upload_id)
        return self._get_object_by_key(owner, key)

    def delete_session_file(
        self,
        owner: str,
        session_id: str,
        upload_id: str,
    ) -> bool:
        """Delete a session-scoped file. Returns True on success."""
        key = self.session_file_path(session_id, upload_id)
        return self._delete_object_by_key(owner, key)

    def list_session_files(self, owner: str, session_id: str) -> Iterator[str]:
        """List all files in a session's uploads directory."""
        prefix = f"sessions/{session_id}/uploads/"
        full_prefix = self._full_key(owner, prefix)
        if not self.healthy:
            return iter(())
        
        try:
            for obj in self._client.list_objects(_BUCKET, prefix=full_prefix, recursive=True):
                yield obj.object_name
        except Exception as exc:
            logger.error("list_session_files failed for %s: %s", full_prefix, exc)
            return iter(())

    # ── Library file operations ──────────────────────────────────────

    def put_library_file(
        self,
        owner: str,
        doc_id: str,
        data: bytes | bytearray | str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a persistent library document.
        
        Path: userdata/{owner}/library/{doc_id}
        Returns the full object key written.
        """
        key = self.library_file_path(doc_id)
        if isinstance(data, str):
            data = data.encode("utf-8")
        
        full_key = self._full_key(owner, key)
        import io
        stream = io.BytesIO(data)
        
        self._client.put_object(
            bucket_name=_BUCKET,
            object_name=full_key,
            data=stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info("put_library_file: SUCCESS owner=%s doc=%s", owner, doc_id)
        return full_key

    def get_library_file(self, owner: str, doc_id: str) -> Optional[bytes]:
        """Download a library document. Returns None if not found."""
        key = self.library_file_path(doc_id)
        return self._get_object_by_key(owner, key)

    def delete_library_file(self, owner: str, doc_id: str) -> bool:
        """Delete a library document. Returns True on success."""
        key = self.library_file_path(doc_id)
        return self._delete_object_by_key(owner, key)

    def list_library_files(self, owner: str) -> Iterator[str]:
        """List all files in a user's library."""
        prefix = "library/"
        full_prefix = self._full_key(owner, prefix)
        if not self.healthy:
            return iter(())

        try:
            for obj in self._client.list_objects(_BUCKET, prefix=full_prefix, recursive=True):
                yield obj.object_name
        except Exception as exc:
            logger.error("list_library_files failed for %s: %s", full_prefix, exc)
            return iter(())

    # ── Brain file operations ────────────────────────────────────────

    def put_brain(
        self,
        owner: str,
        brain_name: str,
        data: bytes | bytearray | str,
        content_type: str = "application/octet-stream",
    ) -> str:
        """Upload a per-user "core brain" config file.

        Path: userdata/{owner}/brains/{brain_name}
        Returns the full object key written.
        """
        key = _brain_file_path(brain_name)
        full_key = self._full_key(owner, key)
        if isinstance(data, str):
            data = data.encode("utf-8")
        import io
        stream = io.BytesIO(data)
        self._client.put_object(
            bucket_name=_BUCKET,
            object_name=full_key,
            data=stream,
            length=len(data),
            content_type=content_type,
        )
        logger.info("put_brain: SUCCESS owner=%s brain=%s", owner, brain_name)
        return full_key

    def get_brain(self, owner: str, brain_name: str) -> Optional[bytes]:
        """Download a per-user brain config. Returns None if not found."""
        key = _brain_file_path(brain_name)
        return self._get_object_by_key(owner, key)

    def delete_brain(self, owner: str, brain_name: str) -> bool:
        """Delete a per-user brain config. Returns True on success."""
        key = _brain_file_path(brain_name)
        return self._delete_object_by_key(owner, key)

    def list_brains(self, owner: str) -> Iterator[str]:
        """List all brain config files for a user."""
        prefix = "brains/"
        full_prefix = self._full_key(owner, prefix)
        if not self.healthy:
            return iter(())
        try:
            for obj in self._client.list_objects(_BUCKET, prefix=full_prefix, recursive=True):
                yield obj.object_name
        except Exception as exc:
            logger.error("list_brains failed for %s: %s", full_prefix, exc)
            return iter(())

    # ── Internal helpers ────────────────────────────────────────────

    def _get_object_by_key(self, owner: str, key: str) -> Optional[bytes]:
        """Internal helper to get object by computed key."""
        if not self.healthy:
            return None
        
        from minio.error import S3Error
        full_key = self._full_key(owner, key)
        try:
            response = self._client.get_object(_BUCKET, full_key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            if "NoSuchKey" not in str(exc):
                logger.error("get_object failed for %s: %s", full_key, exc)
            return None
        except Exception as exc:
            logger.error("get_object failed for %s: %s", full_key, exc)
            return None

    def _delete_object_by_key(self, owner: str, key: str) -> bool:
        """Internal helper to delete object by computed key."""
        if not self.healthy:
            return False
        
        from minio.error import S3Error
        full_key = self._full_key(owner, key)
        try:
            self._client.remove_object(_BUCKET, full_key)
            return True
        except S3Error as exc:
            logger.error("remove_object failed for %s: %s", full_key, exc)
            return False
        except Exception as exc:
            logger.error("remove_object failed for %s: %s", full_key, exc)
            return False


# Process-wide singleton
store = ObjectStore()
