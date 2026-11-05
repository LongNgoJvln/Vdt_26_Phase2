# src/middleware.py
# Shared middleware, decorators, and request helpers

import os
import secrets
import uuid
import time
import logging

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)

# Per-process identifier — lets log aggregation group requests by process
_PROCESS_ID = uuid.uuid4().hex[:8]

# Per-process token that lets the in-app tool layer hit admin-gated
# routes via HTTP loopback (the agent's tool calls don't carry the
# admin user's session cookie). Set once at import; tools read the
# same value from this module. Never persisted or exposed externally.
INTERNAL_TOOL_TOKEN = os.environ.get("ODYSSEUS_INTERNAL_TOKEN") or secrets.token_hex(32)
INTERNAL_TOOL_HEADER = "X-VHTNA-Internal-Token"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Attach a unique request ID (X-Request-Id) to every request/response.

    The ID is:
    - Read from the client's ``X-Request-Id`` header if present (for
      distributed tracing where the caller assigns IDs).
    - Otherwise generated as a short UUID hex string.

    Stored on ``request.state.request_id`` and emitted as a response header
    so callers can correlate logs across hops.  A short log line is written
    at completion time with method, path, status, and duration, making it
    easy to grep the request flow end-to-end.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Reuse caller-provided ID for distributed tracing, else generate.
        req_id = request.headers.get("X-Request-Id") or uuid.uuid4().hex[:16]
        request.state.request_id = req_id
        request.state.process_id = _PROCESS_ID

        _start = time.monotonic()
        _method = request.method
        _path = request.url.path

        try:
            response = await call_next(request)
        except Exception as exc:
            logger.error(
                "[req_id=%s] %s %s — unhandled exception in %.1fms",
                req_id, _method, _path,
                (time.monotonic() - _start) * 1000,
                exc_info=True,
            )
            raise

        duration_ms = (time.monotonic() - _start) * 1000
        response.headers["X-Request-Id"] = req_id

        # Log at INFO for slow requests (>=500ms) or non-2xx, else DEBUG.
        _status = response.status_code
        if duration_ms >= 500 or _status >= 400:
            logger.info(
                "[req_id=%s] %s %s → %d (%.1fms, proc=%s)",
                req_id, _method, _path, _status, duration_ms, _PROCESS_ID,
            )
        else:
            logger.debug(
                "[req_id=%s] %s %s → %d (%.1fms)",
                req_id, _method, _path, _status, duration_ms,
            )

        return response


def require_admin(request: Request):
    """Raise 403 if the current user isn't an admin.
    Allows access when auth is explicitly disabled, or when the request carries
    the in-process internal-tool token used by loopback agent tools.
    """
    # In-process bypass for tool-layer loopback calls. Two paths:
    # (a) header-direct (caller set X-VHTNA-Internal-Token), or
    # (b) the auth middleware already validated the token and stamped
    #     request.state.current_user = "internal-tool".
    try:
        hdr = request.headers.get(INTERNAL_TOOL_HEADER)
        if hdr and secrets.compare_digest(hdr, INTERNAL_TOOL_TOKEN):
            return
        if getattr(request.state, "current_user", None) == "internal-tool":
            return
    except Exception:
        pass

    auth_mgr = getattr(request.app.state, "auth_manager", None)
    if os.getenv("AUTH_ENABLED", "true").lower() == "false":
        return
    if not auth_mgr or not auth_mgr.is_configured:
        raise HTTPException(403, "Admin only")
    user = getattr(request.state, "current_user", None)
    if not user or not auth_mgr.is_admin(user):
        raise HTTPException(403, "Admin only")


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add standard security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        # Generate a per-request nonce for inline scripts
        nonce = secrets.token_hex(16)
        request.state.csp_nonce = nonce

        response = await call_next(request)
        path = request.url.path

        # Tool render endpoints are served inside iframes — allow framing by self
        is_tool_render = path.startswith("/api/tools/") and path.endswith("/render")
        # Visual report pages are self-contained HTML — need inline scripts + external images
        is_report = path.startswith("/api/research/report/")

        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "no-referrer"

        if is_report:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "font-src 'self'; "
                "img-src 'self' data: blob: https:; "
                "connect-src 'self'; "
                "frame-ancestors 'none'"
            )
        elif is_tool_render:
            # Tool iframe content: skip all framing headers — the iframe's
            # sandbox="allow-scripts" attribute provides isolation.
            # Don't overwrite the route's own restrictive CSP either.
            pass
        else:
            response.headers["X-Frame-Options"] = "DENY"
            # NOTE: `style-src 'unsafe-inline'` is intentionally retained.
            # `static/index.html` and `static/login.html` ship inline <style>
            # blocks, and several JS modules build runtime `style=""` attrs.
            # Migrating to nonce-only requires templating the HTML files +
            # auditing every JS-set style attribute. Since inline styles
            # don't execute script, the residual risk is visual-only.
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                f"script-src 'self' 'nonce-{nonce}' https://cdn.jsdelivr.net; "
                "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
                "font-src 'self' https://cdn.jsdelivr.net; "
                "img-src 'self' data: blob:; "
                "media-src 'self' blob:; "
                "connect-src 'self'; "
                "frame-src 'self'; "
                "frame-ancestors 'none'"
            )
        return response
