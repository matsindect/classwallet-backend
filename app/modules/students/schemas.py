"""Pydantic schemas for student request validation and response serialisation.

All schemas inherit from ``CamelModel`` so field names are serialised as
camelCase in JSON responses (e.g. ``first_name`` -> ``firstName``).
"""

import json
from datetime import datetime

from app.core.schemas import CamelModel

# ---------------------------------------------------------------------------
# Guardian schemas
# ---------------------------------------------------------------------------


class GuardianCreate(CamelModel):
    """Schema for creating a guardian alongside a student."""

    first_name: str
    last_name: str
    relationship: str
    phone: str
    email: str | None = None
    is_primary: bool = False


class GuardianResponse(CamelModel):
    """Response schema for a guardian record."""

    id: str
    first_name: str
    last_name: str
    relationship: str
    phone: str
    email: str | None = None
    is_primary: bool


# ---------------------------------------------------------------------------
# Student schemas
# ---------------------------------------------------------------------------


class StudentCreate(CamelModel):
    """Schema for creating a new student.

    ``guardians`` is optional so the CSV import flow (which does not supply
    structured guardian objects) continues to work.
    """

    first_name: str
    last_name: str
    grade: str
    class_name: str | None = None
    date_of_birth: str | None = None
    guardians: list[GuardianCreate] | None = None


class StudentUpdate(CamelModel):
    """Schema for partially updating an existing student.

    All fields are optional; only fields explicitly set will be applied.
    When ``guardians`` is provided the existing guardians are fully replaced.
    """

    first_name: str | None = None
    last_name: str | None = None
    grade: str | None = None
    class_name: str | None = None
    status: str | None = None
    date_of_birth: str | None = None
    guardians: list[GuardianCreate] | None = None


class StudentResponse(CamelModel):
    """Response schema returned when reading a student record."""

    id: str
    student_id: str | None = None
    first_name: str
    last_name: str
    grade: str | None = None
    class_name: str | None = None
    status: str
    date_of_birth: str | None = None
    guardians: list[GuardianResponse] = []
    enrollment_date: str | None = None
    balance: float = 0.0
    created_at: datetime
    updated_at: datetime


class StudentImportResponse(CamelModel):
    """Response schema for a CSV student import result."""

    id: str
    file_name: str
    total_rows: int
    success_rows: int
    error_rows: int
    status: str
    errors: list[dict] | None = None
    created_at: datetime
    completed_at: datetime | None = None

    @classmethod
    def from_import(cls, imp: object) -> "StudentImportResponse":
        """Build a response from a ``StudentImport`` ORM model.

        Maps the ORM field names (``successful_rows``, ``failed_rows``) to the
        API contract names (``success_rows``, ``error_rows``) and deserialises
        the JSON ``errors`` string.
        """
        errors_parsed: list[dict] | None = None
        raw_errors = getattr(imp, "errors", None)
        if raw_errors:
            try:
                errors_parsed = json.loads(raw_errors)
            except (json.JSONDecodeError, TypeError):
                errors_parsed = None

        return cls(
            id=imp.id,  # type: ignore[union-attr]
            file_name=imp.file_name,  # type: ignore[union-attr]
            total_rows=imp.total_rows,  # type: ignore[union-attr]
            success_rows=imp.successful_rows,  # type: ignore[union-attr]
            error_rows=imp.failed_rows,  # type: ignore[union-attr]
            status=imp.status,  # type: ignore[union-attr]
            errors=errors_parsed,
            created_at=imp.created_at,  # type: ignore[union-attr]
            completed_at=getattr(imp, "completed_at", None),
        )
