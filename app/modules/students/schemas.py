"""Pydantic schemas for student request validation and response serialisation.

Provides input schemas for creating and updating students, as well as
response schemas for individual students and CSV import results.
"""

from datetime import datetime

from pydantic import BaseModel


class StudentCreate(BaseModel):
    """Schema for creating a new student.

    All fields are optional so the caller can supply only the known
    attributes; ``school_id`` is inferred from the authenticated user.

    Attributes:
        first_name: Student's first name.
        last_name: Student's last name.
        email: Optional email address.
        phone: Optional phone number.
        grade: Optional grade/class level.
        status: Optional enrolment status.
        guardian_name: Optional guardian full name.
        guardian_email: Optional guardian email.
        guardian_phone: Optional guardian phone number.
    """
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    grade: str | None = None
    status: str | None = None
    guardian_name: str | None = None
    guardian_email: str | None = None
    guardian_phone: str | None = None


class StudentUpdate(BaseModel):
    """Schema for partially updating an existing student.

    Only fields that are explicitly set (``exclude_unset=True``) will be
    applied to the student record.

    Attributes:
        first_name: Updated first name.
        last_name: Updated last name.
        email: Updated email address.
        phone: Updated phone number.
        grade: Updated grade/class level.
        status: Updated enrolment status.
        guardian_name: Updated guardian full name.
        guardian_email: Updated guardian email.
        guardian_phone: Updated guardian phone number.
    """
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    phone: str | None = None
    grade: str | None = None
    status: str | None = None
    guardian_name: str | None = None
    guardian_email: str | None = None
    guardian_phone: str | None = None


class StudentResponse(BaseModel):
    """Response schema returned when reading a student record.

    Populated from the ``Student`` ORM model via ``from_attributes`` mode.
    """
    id: str
    school_id: str
    first_name: str
    last_name: str
    email: str | None = None
    phone: str | None = None
    grade: str | None = None
    status: str
    guardian_name: str | None = None
    guardian_email: str | None = None
    guardian_phone: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentImportResponse(BaseModel):
    """Response schema for a CSV student import result.

    Contains row-level statistics and any error details from the import.
    Populated from the ``StudentImport`` ORM model via ``from_attributes`` mode.
    """
    id: str
    school_id: str
    file_name: str
    total_rows: int
    successful_rows: int
    failed_rows: int
    status: str
    errors: str | None = None
    created_by: str
    created_at: datetime

    model_config = {"from_attributes": True}
