"""Uniform API response envelope.

Every endpoint returns this structure so the frontend can parse responses
consistently:

    {
        "success": true/false,
        "data": T | null,
        "error": { "code": "...", "message": "...", "details": {...} } | null,
        "meta": { "page": 1, "pageSize": 10, ... } | null
    }
"""

from typing import Any

from pydantic import BaseModel


class ApiError(BaseModel):
    """Error object inside the response envelope."""

    code: str
    message: str
    details: dict[str, list[str]] | None = None


class PaginationMeta(BaseModel):
    """Pagination metadata inside the response envelope."""

    page: int
    pageSize: int  # noqa: N815
    totalCount: int  # noqa: N815
    totalPages: int  # noqa: N815


class ApiResponse(BaseModel):
    """Uniform response envelope for all API endpoints."""

    success: bool
    data: Any = None
    error: ApiError | None = None
    meta: PaginationMeta | None = None


def success_response(
    data: Any = None,
    meta: dict | PaginationMeta | None = None,
) -> dict:
    """Build a success envelope."""
    envelope: dict[str, Any] = {
        "success": True,
        "data": data,
        "error": None,
        "meta": meta,
    }
    return envelope


def error_response(
    code: str,
    message: str,
    details: dict[str, list[str]] | None = None,
) -> dict:
    """Build an error envelope."""
    return {
        "success": False,
        "data": None,
        "error": {
            "code": code,
            "message": message,
            **({"details": details} if details else {}),
        },
        "meta": None,
    }


def paginated_response(
    data: list,
    page: int,
    page_size: int,
    total_count: int,
) -> dict:
    """Build a success envelope with pagination metadata."""
    import math

    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return success_response(
        data=data,
        meta={
            "page": page,
            "pageSize": page_size,
            "totalCount": total_count,
            "totalPages": total_pages,
        },
    )
