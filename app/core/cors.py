"""CORS configuration with wildcard subdomain support.

Allows exact origins from CORS_ORIGINS config, plus any subdomain
matching ``*.lovableproject.com`` or ``*.lovable.app``.
"""

import re

from fastapi import FastAPI
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import settings

# Wildcard patterns for allowed origin suffixes
WILDCARD_PATTERNS = [
    re.compile(r"^https?://.*\.lovableproject\.com$"),
    re.compile(r"^https?://.*\.lovable\.app$"),
]


def is_origin_allowed(origin: str) -> bool:
    """Check if an origin is allowed by exact match or wildcard pattern."""
    if origin in settings.cors_origins_list:
        return True
    return any(pattern.match(origin) for pattern in WILDCARD_PATTERNS)


class DynamicCORSMiddleware(BaseHTTPMiddleware):
    """Single CORS middleware handling both exact origins and wildcard patterns.

    Replaces FastAPI's CORSMiddleware entirely so there is no conflict
    with middleware ordering.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")

        # Non-CORS request — pass through
        if not origin:
            return await call_next(request)

        allowed = is_origin_allowed(origin)

        # Handle preflight (OPTIONS)
        if request.method == "OPTIONS":
            if allowed:
                response = Response(status_code=200)
                response.headers["Access-Control-Allow-Origin"] = origin
                response.headers["Access-Control-Allow-Credentials"] = "true"
                response.headers["Access-Control-Allow-Methods"] = (
                    "GET, POST, PUT, PATCH, DELETE, OPTIONS"
                )
                response.headers["Access-Control-Allow-Headers"] = (
                    "Authorization, Content-Type, X-Request-ID, Accept"
                )
                response.headers["Access-Control-Max-Age"] = "600"
                return response
            # Disallowed origin preflight — return 200 with no CORS headers
            # (browser will block the actual request)
            return Response(status_code=200)

        # Actual request
        response = await call_next(request)

        if allowed:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Credentials"] = "true"

        return response


def add_cors_middleware(app: FastAPI) -> None:
    """Add the dynamic CORS middleware to the FastAPI app."""
    app.add_middleware(DynamicCORSMiddleware)
