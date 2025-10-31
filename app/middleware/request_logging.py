import time
import uuid
import logging
from typing import Callable
from starlette.requests import Request
from starlette.responses import Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.logging_context import request_id_var, session_id_var


logger = logging.getLogger(__name__)


def _extract_session_id(request: Request) -> str | None:
    """Best-effort extraction of a session id from the incoming request.

    Order of precedence:
    - `session_id` query parameter
    - Path pattern `/session/{id}`
    - `X-Session-ID` header
    Returns None if no candidate is found.
    """
    # Prefer query param
    sid = request.query_params.get("session_id")
    if sid:
        return sid
    # From path like /session/{id}
    path = request.url.path.strip("/")
    parts = path.split("/")
    try:
        if len(parts) >= 2 and parts[0] == "session":
            return parts[1]
    except Exception:
        pass
    # Header override
    return request.headers.get("X-Session-ID")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Structured request logging with correlation ids and timing.

    Adds `request_id` and `session_id` context to all logs via ContextVars,
    emits `request.start` and `request.end` events, and attaches the
    `X-Request-ID` header on responses.
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Log request lifecycle and forward to the next ASGI app."""
        start = time.perf_counter()
        rid = str(uuid.uuid4())
        request_id_var.set(rid)
        sid = _extract_session_id(request)
        if sid:
            session_id_var.set(sid)

        # Log request start (avoid body logging to protect PII)
        logger.info(
            "request.start",
            extra={
                "request_id": rid,
                "session_id": sid,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else None,
                "user_agent": request.headers.get("user-agent"),
            },
        )
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = int((time.perf_counter() - start) * 1000)
            logger.exception(
                "request.error",
                extra={
                    "request_id": rid,
                    "session_id": sid,
                    "method": request.method,
                    "path": request.url.path,
                    "duration_ms": duration_ms,
                },
            )
            raise

        duration_ms = int((time.perf_counter() - start) * 1000)
        response.headers["X-Request-ID"] = rid
        logger.info(
            "request.end",
            extra={
                "request_id": rid,
                "session_id": sid,
                "method": request.method,
                "path": request.url.path,
                "status": response.status_code,
                "duration_ms": duration_ms,
                "length": response.headers.get("content-length"),
            },
        )
        return response
