"""Tests for the MinIO required-vs-enabled distinction in ``save_upload``.

When the operator opts into MinIO (``ODYSSEUS_USE_MINIO=true``) but the
object store is unreachable at runtime, ``save_upload`` must reject the
upload with HTTP 503 — NOT silently fall back to local FS. The old
silent-fallback behaviour masked broken deployments and lost uploads.

These cover three states:
* opted-in + unreachable at init  -> 503
* opted-in + healthy probe, put fails at runtime -> 503
* opted-out -> local-FS write succeeds, no minio_key
"""
import io
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from fastapi import HTTPException  # type: ignore
except Exception:  # pragma: no cover
    class HTTPException(Exception):
        def __init__(self, status_code: int, detail: str = ""):
            self.status_code = status_code
            self.detail = detail
            super().__init__(detail)

from src.upload_handler import UploadHandler  # noqa: E402


class _BrokenStore:
    """Mimics ODYSSEUS_USE_MINIO=true with MinIO unreachable at startup.

    ``enabled`` reflects the env var (True); ``healthy`` reflects actual
    connectivity (False). ``put_user_object`` must never be called.
    """
    enabled = True
    healthy = False

    def put_user_object(self, *a, **kw):  # pragma: no cover - safety net
        raise RuntimeError("should not be called on an unhealthy store")


class _PutFailsStore:
    """Healthy at probe time, raises during the actual put_object call.

    Catches the case where MinIO was reachable at init but the network
    broke mid-request. Same posture: reject loudly, don't fall back.
    """
    enabled = True
    healthy = True

    def put_user_object(self, *a, **kw):
        raise RuntimeError("connection reset mid-put")


def _stub_upload(name: str, body: bytes) -> SimpleNamespace:
    return SimpleNamespace(
        filename=name,
        file=io.BytesIO(body),
        content_type="application/octet-stream",
        size=len(body),
    )


def _make_handler(store, monkeypatch, tmp_path) -> UploadHandler:
    monkeypatch.setenv("ODYSSEUS_USE_MINIO", "true")
    handler = UploadHandler(
        base_dir=str(tmp_path / "base"),
        upload_dir=str(tmp_path / "up"),
    )
    handler.upload_rate_limit = 100
    handler.object_store = store
    return handler


def test_required_but_unhealthy_rejects(monkeypatch, tmp_path):
    """Opted-in + store probe failed -> 503, no local fallback write."""
    handler = _make_handler(_BrokenStore(), monkeypatch, tmp_path)
    upload = _stub_upload("hi.png", b"\x89PNG\r\n\x1a\n" + b"x" * 32)

    with pytest.raises(HTTPException) as exc:
        handler.save_upload(upload, "1.2.3.4", owner="alice", file_scope="library")

    assert exc.value.status_code == 503
    assert "not saved" in exc.value.detail.lower()


def test_healthy_but_put_fails_rejects(monkeypatch, tmp_path):
    """Opted-in + healthy probe + put_object raises -> 503."""
    handler = _make_handler(_PutFailsStore(), monkeypatch, tmp_path)
    upload = _stub_upload("hi.png", b"\x89PNG\r\n\x1a\n" + b"y" * 32)

    with pytest.raises(HTTPException) as exc:
        handler.save_upload(upload, "1.2.3.4", owner="alice", file_scope="library")

    assert exc.value.status_code == 503


def test_opted_out_still_writes_local(monkeypatch, tmp_path):
    """ODYSSEUS_USE_MINIO=false -> local FS write succeeds, no minio_key.

    Regression guard for the non-MinIO deployment path.
    """
    monkeypatch.setenv("ODYSSEUS_USE_MINIO", "false")
    handler = UploadHandler(
        base_dir=str(tmp_path / "base"),
        upload_dir=str(tmp_path / "up"),
    )
    handler.upload_rate_limit = 100
    handler.object_store = None
    upload = _stub_upload("hi.txt", b"hello world")

    meta = handler.save_upload(upload, "1.2.3.4", owner="alice", file_scope="library")

    assert meta is not None
    assert meta.get("minio_key") in (None, "")
    assert Path(meta["path"]).exists()
