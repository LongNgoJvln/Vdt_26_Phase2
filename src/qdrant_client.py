"""qdrant_client.py

Singleton sync Qdrant client shared by VectorRAG, MemoryVectorStore, and
ToolIndex. Qdrant is Odysseus's sole vector store as of 2026-08.
All three callers are entirely synchronous, so we use
:class:`qdrant_client.QdrantClient` — not the async variant.

Environment:
  QDRANT_URL       — fully-qualified URL (default http://localhost:6333;
                     prod is http://172.20.1.109:30633).
  QDRANT_API_KEY   — optional, for cloud-hosted instances.
  QDRANT_TIMEOUT   — request timeout seconds (default 30.0).
  QDRANT_CONNECT_TIMEOUT — TCP/HTTP probe seconds (default 2.0).
"""

from __future__ import annotations

import logging
import os
import socket
import threading
from typing import Optional
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

_client = None
_lock = threading.Lock()

_DEFAULT_URL = "http://localhost:6333"
_DEFAULT_TIMEOUT = 30.0
_CONNECT_TIMEOUT = float(os.getenv("QDRANT_CONNECT_TIMEOUT", "2.0"))


def _port_open(host: str, port: int, timeout: Optional[float] = None) -> bool:
    """Return True if a TCP connection to host:port succeeds within timeout."""
    try:
        with socket.create_connection((host, port), timeout=timeout or _CONNECT_TIMEOUT):
            return True
    except OSError:
        return False


def _resolve_endpoint() -> tuple[str, Optional[str], float, Optional[tuple[str, int]]]:
    """Return (url, api_key, timeout, probe_target).

    ``probe_target`` is (host, port) when the URL is host:port; otherwise
    ``None`` (probe skipped, e.g. when the URL points at a unix socket or is
    otherwise exotic). Probe failure only logs — we still let the caller try
    in case the probe is overly conservative.
    """
    url = os.getenv("QDRANT_URL", _DEFAULT_URL).rstrip("/")
    api_key = os.getenv("QDRANT_API_KEY") or None
    timeout = float(os.getenv("QDRANT_TIMEOUT", str(_DEFAULT_TIMEOUT)))
    probe: Optional[tuple[str, int]] = None
    try:
        parsed = urlparse(url)
        if parsed.hostname:
            port = parsed.port
            if port is None:
                port = 443 if parsed.scheme == "https" else 80
            probe = (parsed.hostname, port)
    except Exception:
        probe = None
    return url, api_key, timeout, probe


def get_qdrant_client():
    """Return the module-level QdrantClient singleton.

    Creates it on first use. Raises ``RuntimeError`` if the package isn't
    installed or the endpoint is unreachable.
    """
    global _client
    if _client is not None:
        return _client

    with _lock:
        if _client is not None:
            return _client

        try:
            from qdrant_client import QdrantClient
        except ImportError as e:
            raise RuntimeError(
                "qdrant-client is not installed. Install with: "
                "pip install 'qdrant-client>=1.11,<2'"
            ) from e

        url, api_key, timeout, probe = _resolve_endpoint()
        if probe is not None and not _port_open(*probe):
            # Don't raise here — the HTTP client may still succeed in some
            # proxy/network setups where the TCP probe is blocked but real
            # requests routed. Log and let the client constructor try.
            logger.warning(
                "Qdrant TCP probe to %s:%s failed; attempting HTTP anyway.",
                probe[0],
                probe[1],
            )

        client = QdrantClient(url=url, api_key=api_key, timeout=timeout)
        # Smoke test — if the server is unreachable, don't cache a dead
        # singleton; let the caller surface the error and the next call retry.
        try:
            client.get_collections()
        except Exception as e:
            logger.error("Qdrant unreachable at %s: %s", url, e)
            raise RuntimeError(
                f"Qdrant is not reachable at {url}. Start the Qdrant service "
                f"or set QDRANT_URL to a running instance. ({e.__class__.__name__}: {e})"
            ) from e

        _client = client
        logger.info("Qdrant connected: %s", url)
        return _client


def reset_client() -> None:
    """Drop the singleton so the next call reconnects.

    Called from routes/embedding_routes.py after the user reconfigures the
    embedding backend (collection dimensions change → fresh connection).
    """
    global _client
    with _lock:
        _client = None


def healthy() -> bool:
    """Return True iff a Qdrant client can be reached right now.

    Used by the upload→RAG ingest pipeline to skip ingestion when the
    vector store is down (mirrors the old ``VectorRAG.healthy`` semantics).
    Never raises — callers rely on the bool.
    """
    try:
        client = get_qdrant_client()
        client.get_collections()
        return True
    except Exception:
        return False
