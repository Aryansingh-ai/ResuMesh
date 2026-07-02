"""Rate limiting middleware using Redis."""

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from loguru import logger

from app.core.config import settings



class RateLimitMiddleware(BaseHTTPMiddleware):
    """Simple token bucket rate limiter using in-memory dict (Redis in production)."""

    def __init__(self, app):
        super().__init__(app)
        self._counters: dict = {}

    async def dispatch(self, request: Request, call_next):
        # Skip rate limiting for health checks
        if request.url.path in {"/health", "/ready", "/metrics"}:
            return await call_next(request)

        client_ip = request.client.host if request.client else "unknown"
        key = f"{client_ip}:{request.url.path}"

        import time
        now = time.time()
        window = settings.RATE_LIMIT_WINDOW_SECONDS
        max_requests = settings.RATE_LIMIT_REQUESTS

        if key not in self._counters:
            self._counters[key] = {"count": 0, "window_start": now}

        entry = self._counters[key]
        if now - entry["window_start"] > window:
            entry["count"] = 0
            entry["window_start"] = now

        entry["count"] += 1

        if entry["count"] > max_requests:
            logger.bind(client_ip=client_ip, path=request.url.path).warning("Rate limit exceeded")
            return JSONResponse(
                status_code=429,
                content={
                    "success": False,
                    "message": "Too many requests. Please slow down.",
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
                headers={"Retry-After": str(window)},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(max(0, max_requests - entry["count"]))
        return response
