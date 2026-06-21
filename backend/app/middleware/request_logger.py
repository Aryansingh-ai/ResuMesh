"""Request logging middleware."""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import structlog

logger = structlog.get_logger(__name__)


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, and duration."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)

        duration_ms = (time.perf_counter() - start_time) * 1000

        logger.info(
            "HTTP request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
            client_ip=request.client.host if request.client else "unknown",
        )

        response.headers["X-Request-ID"] = request_id
        return response
