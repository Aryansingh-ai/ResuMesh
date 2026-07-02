"""Request logging middleware."""

import time
import uuid
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from loguru import logger

class RequestLoggerMiddleware(BaseHTTPMiddleware):
    """Logs every HTTP request with method, path, status, latency, and IP."""

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())[:8]
        start_time = time.perf_counter()

        # Bind request_id to context for downstream loggers (if needed)
        with logger.contextualize(request_id=request_id):
            response = await call_next(request)

            duration_ms = (time.perf_counter() - start_time) * 1000
            client_ip = request.client.host if request.client else "unknown"

            # Format strictly per requirements: method, endpoint, status code, latency, client IP
            logger.info(
                f"HTTP Request - Method: {request.method}, Endpoint: {request.url.path}, "
                f"Status: {response.status_code}, Latency: {duration_ms:.2f}ms, IP: {client_ip}"
            )

            response.headers["X-Request-ID"] = request_id
            return response
