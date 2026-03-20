"""Application-specific error hierarchy and global exception handler.

Defines a base ``AppError`` and specialised subclasses for common HTTP error
scenarios.  Each subclass encodes a fixed status code and a machine-readable
error ``code`` string.  The ``app_error_handler`` function is registered on
the FastAPI app so that any ``AppError`` raised inside a route is
automatically serialised to a consistent JSON envelope.
"""

from fastapi import Request
from fastapi.responses import JSONResponse


class AppError(Exception):
    """Base application error.

    All domain-specific errors inherit from this class.  It carries a
    machine-readable ``code``, a human-readable ``message``, an HTTP
    ``status_code``, and optional ``details`` for field-level validation
    information.

    Attributes:
        code: Short machine-readable error identifier (e.g. ``"AUTH_ERROR"``).
        message: Human-readable description of the error.
        status_code: HTTP status code to return to the client.
        details: Optional mapping of field names to lists of error messages.
    """

    def __init__(
        self,
        code: str = "APP_ERROR",
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
        super().__init__(code="AUTH_ERROR", message=message, status_code=401, details=details)


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
    """Input validation failure (HTTP 422 Unprocessable Entity)."""

    def __init__(
        self,
        message: str = "Validation failed",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="VALIDATION_ERROR", message=message, status_code=422, details=details)


class ConflictError(AppError):
    """Resource state conflict (HTTP 409 Conflict)."""

    def __init__(
        self,
        message: str = "Resource conflict",
        details: dict[str, list[str]] | None = None,
    ):
        super().__init__(code="CONFLICT", message=message, status_code=409, details=details)


async def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
    """Global exception handler registered on the FastAPI application.

    Converts any ``AppError`` into a JSON response with the structure::

        {"code": "...", "message": "...", "details": {...}}

    The ``details`` key is included only when the error carries field-level
    information.

    Args:
        _request: The incoming Starlette request (unused).
        exc: The ``AppError`` instance that was raised.

    Returns:
        A ``JSONResponse`` with the appropriate HTTP status code and body.
    """
    body: dict = {"code": exc.code, "message": exc.message}
    if exc.details:
        body["details"] = exc.details
    return JSONResponse(status_code=exc.status_code, content=body)
