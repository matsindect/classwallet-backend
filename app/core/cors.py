"""CORS configuration with wildcard subdomain support.

Allows exact origins from CORS_ORIGINS config, plus any subdomain
matching ``*.lovableproject.com`` or ``*.lovable.app``.
"""

import re

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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
    """Middleware that checks origin against exact list + wildcard patterns.

    For allowed origins, sets the standard CORS headers. Preflight
    (OPTIONS) requests are handled with a 200 response.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        origin = request.headers.get("origin")

        # Non-CORS request — pass through
        if not origin:
            return await call_next(request)

        # Check if origin is allowed
        if not is_origin_allowed(origin):
            return await call_next(request)

        # Handle preflight
        if request.method == "OPTIONS":
            response = Response(status_code=200)
        else:
            response = await call_next(request)

        # Set CORS headers — mirror the specific origin (not *)
        response.headers["Access-Control-Allow-Origin"] = origin
        response.headers["Access-Control-Allow-Credentials"] = "true"
        response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, PATCH, DELETE, OPTIONS"
        response.headers["Access-Control-Allow-Headers"] = (
            "Authorization, Content-Type, X-Request-ID"
        )
        response.headers["Access-Control-Max-Age"] = "600"

        return response


def add_cors_middleware(app: FastAPI) -> None:
    """Add CORS middleware to the FastAPI app.

    Uses exact origins from settings for standard CORSMiddleware,
    and adds the dynamic middleware for wildcard subdomain matching.
    """
    # Dynamic middleware for wildcard patterns (runs first)
    app.add_middleware(DynamicCORSMiddleware)

    # Standard CORSMiddleware for exact origins (fallback)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
