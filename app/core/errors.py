"""Application-specific error hierarchy and global exception handler.

Defines a base ``AppError`` and specialised subclasses for common HTTP error
scenarios.  The ``app_error_handler`` wraps every error in the uniform
``{success, data, error, meta}`` envelope expected by the frontend.
"""

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.response import error_response


class AppError(Exception):
    """Base application error."""

    def __init__(
        self,
        code: str = "INTERNAL_ERROR",
        message: str = "An unexpected error occurred",
        status_code: int = 500,
        details: dict[str, list[str]] | None = None,
    ):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)


class AuthError(AppError):
    """Authentication failure (HTTP 401 Unauthorized)."""

    def __init__(
        self,
        message: str = "Authentication failed",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="UNAUTHORIZED", message=message, status_code=401, details=details)


class ForbiddenError(AppError):
    """Authorisation failure (HTTP 403 Forbidden)."""

    def __init__(
        self,
        message: str = "Permission denied",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="FORBIDDEN", message=message, status_code=403, details=details)


class NotFoundError(AppError):
    """Requested resource does not exist (HTTP 404 Not Found)."""

    def __init__(
        self,
        message: str = "Resource not found",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="NOT_FOUND", message=message, status_code=404, details=details)


class ValidationError(AppError):
    """Input validation failure (HTTP 400 Bad Request)."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=400, details=details)


class ConflictError(AppError):
    """Resource state conflict (HTTP 409 Conflict)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="CONFLICT", message=message, status_code=409, details=details)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Global exception handler — wraps errors in the uniform envelope."""
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response(
            code=exc.code,
            message=exc.message,
            details=exc.details,
        ),
    )


async def unhandled_error_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions — returns INTERNAL_ERROR."""
    return JSONResponse(
        status_code=500,
        content=error_response(
            code="INTERNAL_ERROR",
            message="An unexpected error occurred",
        ),
    )
