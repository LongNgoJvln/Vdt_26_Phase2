"""
core/response_types.py

Standardized API response models for consistent error/success formatting
across all VHT Network Automation API endpoints.

Usage:
    from core.response_types import err, ok

    # Error responses
    return err("SESSION_NOT_FOUND", "Session 'xyz' not found", status=404)

    # Success responses
    return ok({"id": "abc", "name": "My Session"})

    # Paginated
    return ok({"items": [...], "total": 42}, meta={"page": 1, "per_page": 20})

All responses follow the same envelope:
    { "ok": true|false, "data": {...}, "error": "...", "message": "...", "meta": {...} }
"""

from typing import Any, Dict, Optional
from fastapi.responses import JSONResponse


# ── Response envelope keys ─────────────────────────────────────────────

def _envelope(
    ok: bool,
    data: Any = None,
    error: Optional[str] = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Build a standard response envelope."""
    body: Dict[str, Any] = {"ok": ok}
    if data is not None:
        body["data"] = data
    if error is not None:
        body["error"] = error
    if message is not None:
        body["message"] = message
    if meta:
        body["meta"] = meta
    return body


# ── Public helpers ─────────────────────────────────────────────────────

def ok(
    data: Any = None,
    message: Optional[str] = None,
    meta: Optional[Dict[str, Any]] = None,
    status: int = 200,
) -> JSONResponse:
    """Return a success response.

    Args:
        data: Response payload (dict, list, scalar).
        message: Optional human-readable success message.
        meta: Optional metadata (pagination, timing, etc.).
        status: HTTP status code (default 200).
    """
    return JSONResponse(
        content=_envelope(ok=True, data=data, message=message, meta=meta),
        status_code=status,
    )


def err(
    error: str,
    message: str = "",
    data: Any = None,
    status: int = 400,
    meta: Optional[Dict[str, Any]] = None,
) -> JSONResponse:
    """Return an error response.

    Args:
        error: Machine-readable error code (e.g. ``"SESSION_NOT_FOUND"``).
        message: Human-readable error description.
        data: Optional additional error context.
        status: HTTP status code (default 400).
        meta: Optional metadata.
    """
    return JSONResponse(
        content=_envelope(ok=False, error=error, message=message, data=data, meta=meta),
        status_code=status,
    )


# ── Standard error codes ───────────────────────────────────────────────

# These constants should be used as the ``error`` argument to ``err()``
# so that clients can reliably switch on them.

E_SESSION_NOT_FOUND = "SESSION_NOT_FOUND"
E_INVALID_FILE_UPLOAD = "INVALID_FILE_UPLOAD"
E_LLM_SERVICE_ERROR = "LLM_SERVICE_ERROR"
E_WEB_SEARCH_ERROR = "WEB_SEARCH_ERROR"
E_NOT_AUTHENTICATED = "NOT_AUTHENTICATED"
E_NOT_AUTHORIZED = "NOT_AUTHORIZED"
E_NOT_FOUND = "NOT_FOUND"
E_VALIDATION_ERROR = "VALIDATION_ERROR"
E_RATE_LIMITED = "RATE_LIMITED"
E_INTERNAL_ERROR = "INTERNAL_ERROR"
E_SERVICE_UNAVAILABLE = "SERVICE_UNAVAILABLE"
E_CONFLICT = "CONFLICT"
E_BAD_REQUEST = "BAD_REQUEST"
E_TIMEOUT = "TIMEOUT"


# ── Helpers for common error cases ─────────────────────────────────────

def not_found(entity: str = "Resource", id: Optional[str] = None) -> JSONResponse:
    """Return a 404 error for a missing entity."""
    msg = f"{entity} not found" + (f" ({id})" if id else "")
    return err(E_NOT_FOUND, msg, status=404)


def not_authenticated(message: str = "Not authenticated") -> JSONResponse:
    """Return a 401 error."""
    return err(E_NOT_AUTHENTICATED, message, status=401)


def not_authorized(message: str = "Admin only") -> JSONResponse:
    """Return a 403 error."""
    return err(E_NOT_AUTHORIZED, message, status=403)


def validation_error(message: str = "Invalid input", details: Any = None) -> JSONResponse:
    """Return a 422/400 validation error."""
    return err(E_VALIDATION_ERROR, message, data=details, status=422)


def rate_limited(message: str = "Too many requests") -> JSONResponse:
    """Return a 429 rate-limit error."""
    return err(E_RATE_LIMITED, message, status=429)


def internal_error(message: str = "Internal server error") -> JSONResponse:
    """Return a 500 error."""
    return err(E_INTERNAL_ERROR, message, status=500)


def service_unavailable(service: str = "") -> JSONResponse:
    """Return a 503 error indicating a downstream dependency is unavailable."""
    msg = f"{service} unavailable" if service else "Service unavailable"
    return err(E_SERVICE_UNAVAILABLE, msg, status=503)
