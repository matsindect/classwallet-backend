"""Generic pagination helpers for list endpoints.

Provides Pydantic response schemas and utility functions that standardise
paginated responses across all list-style API routes.
"""

import math
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

from app.core.config import settings

T = TypeVar("T")


class PaginationMeta(BaseModel):
    """Metadata about the current page of results.

    Attributes:
        page: Current page number (1-based).
        pageSize: Number of items per page.
        totalCount: Total number of items across all pages.
        totalPages: Total number of pages.
    """

    page: int
    pageSize: int
    totalCount: int
    totalPages: int


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic wrapper for paginated API responses.

    Attributes:
        data: The list of items for the current page.
        meta: Pagination metadata (page number, totals, etc.).
    """

    data: list[T]
    meta: PaginationMeta


def paginate(
    items: list[Any],
    total_count: int,
    page: int,
    page_size: int,
) -> dict:
    """Build a paginated response dictionary.

    Args:
        items: The items for the current page.
        total_count: Total number of items across all pages.
        page: Current page number (1-based).
        page_size: Number of items per page.

    Returns:
        A dictionary with ``"data"`` and ``"meta"`` keys matching the
        ``PaginatedResponse`` schema.
    """
    total_pages = math.ceil(total_count / page_size) if page_size > 0 else 0
    return {
        "data": items,
        "meta": {
            "page": page,
            "pageSize": page_size,
            "totalCount": total_count,
            "totalPages": total_pages,
        },
    }


def clamp_pagination(page: int | None, page_size: int | None) -> tuple[int, int]:
    """Sanitise and clamp raw pagination query parameters.

    Ensures that ``page`` is at least 1 and ``page_size`` falls within
    ``[1, settings.MAX_PAGE_SIZE]``.  ``None`` values are replaced with
    sensible defaults.

    Args:
        page: Requested page number (may be ``None``).
        page_size: Requested page size (may be ``None``).

    Returns:
        A ``(page, page_size)`` tuple with safe, bounded values.
    """
    p = max(1, page or 1)
    ps = min(max(1, page_size or settings.DEFAULT_PAGE_SIZE), settings.MAX_PAGE_SIZE)
    return p, ps
