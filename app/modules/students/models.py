"""SQLAlchemy models for the students module.

Defines the ``Student`` and ``StudentImport`` ORM models that map to the
``students`` and ``student_imports`` database tables respectively.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Student(Base):
    """Represents a student enrolled at a school.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the school the student belongs to.
        first_name: Student's first name.
        last_name: Student's last name.
        email: Optional student email address.
        phone: Optional student phone number.
        grade: Optional grade/class level (e.g. "Grade 5").
        status: Enrolment status, defaults to "active".
        guardian_name: Optional name of the student's guardian.
        guardian_email: Optional guardian email address.
        guardian_phone: Optional guardian phone number.
        created_at: Timestamp of record creation (UTC).
        updated_at: Timestamp of last update (UTC), auto-updated on change.
    """
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="active")
    guardian_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guardian_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class StudentImport(Base):
    """Records the result of a bulk CSV student import operation.

    Each row tracks a single import attempt including the file name,
    row counts (total, successful, failed), overall status, and any
    per-row error details serialised as JSON.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the school.
        file_name: Original name of the uploaded CSV file.
        total_rows: Number of data rows found in the CSV.
        successful_rows: Number of rows successfully imported.
        failed_rows: Number of rows that failed validation or insertion.
        status: Import status, defaults to "completed".
        errors: Optional JSON string containing per-row error details.
        created_by: Foreign key referencing the user who triggered the import.
        created_at: Timestamp of import execution (UTC).
    """
    __tablename__ = "student_imports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_rows: Mapped[int] = mapped_column(Integer, default=0)
    successful_rows: Mapped[int] = mapped_column(Integer, default=0)
    failed_rows: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    errors: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
