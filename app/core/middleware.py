"""Custom ASGI middleware for request tracing and logging.

Contains ``RequestIdMiddleware``, which assigns every incoming HTTP request
a unique UUID, measures its duration, and emits a structured log entry when
the response is sent.
"""

import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import get_logger

logger = get_logger("middleware")


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Middleware that assigns a unique ID to every HTTP request.

    For each incoming request this middleware:

    1. Generates a UUID v4 and stores it on ``request.state.request_id``.
    2. Measures wall-clock duration of the downstream handler.
    3. Attaches the ID as an ``X-Request-ID`` response header.
    4. Emits a structured log entry with method, path, status code, and
       duration.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Process an incoming request through the middleware pipeline.

        Args:
            request: The incoming HTTP request.
            call_next: Callable that forwards the request to the next
                middleware or route handler.

        Returns:
            The HTTP response with an ``X-Request-ID`` header attached.
        """
        request_id = str(uuid.uuid4())
        request.state.request_id = request_id
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = round((time.perf_counter() - start) * 1000, 2)
        response.headers["X-Request-ID"] = request_id
        fallback_ip = request.client.host if request.client else "unknown"
        client_ip = request.headers.get("x-forwarded-for", fallback_ip)
        logger.info(
            "request_completed",
            request_id=request_id,
            client_ip=client_ip,
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            duration_ms=duration_ms,
        )
        return response
