"""SQLAlchemy models for the students module.

Defines the ``Student``, ``Guardian``, and ``StudentImport`` ORM models that
map to the ``students``, ``guardians``, and ``student_imports`` database tables
respectively.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Student(Base):
    """Represents a student enrolled at a school.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the school the student belongs to.
        student_id: Optional display ID (e.g. "ARH-2024-001").
        first_name: Student's first name.
        last_name: Student's last name.
        email: Optional student email address.
        phone: Optional student phone number.
        grade: Optional grade/class level (e.g. "Form 4").
        class_name: Optional class name (e.g. "Science A").
        status: Enrolment status, defaults to "ACTIVE".
        date_of_birth: Optional date of birth as YYYY-MM-DD string.
        enrollment_date: Optional enrollment date as YYYY-MM-DD string.
        balance: Outstanding fee balance, defaults to 0.0.
        guardian_name: Legacy — optional name of the student's guardian.
        guardian_email: Legacy — optional guardian email address.
        guardian_phone: Legacy — optional guardian phone number.
        created_at: Timestamp of record creation (UTC).
        updated_at: Timestamp of last update (UTC), auto-updated on change.
    """

    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[str | None] = mapped_column(String(50), nullable=True, unique=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    class_name: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    date_of_birth: Mapped[str | None] = mapped_column(String(20), nullable=True)
    enrollment_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    guardian_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    guardian_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    guardians = relationship(
        "Guardian",
        backref="student",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Guardian(Base):
    """Represents a guardian/parent associated with a student.

    Attributes:
        id: UUID primary key.
        student_id: Foreign key referencing the student.
        first_name: Guardian's first name.
        last_name: Guardian's last name.
        relationship: Relationship to the student (e.g. "Mother", "Father").
        phone: Guardian's phone number.
        email: Optional guardian email address.
        is_primary: Whether this is the primary guardian.
    """

    __tablename__ = "guardians"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    relationship: Mapped[str] = mapped_column(String(50), nullable=False)
    phone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_primary: Mapped[bool] = mapped_column(Boolean, default=False)


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
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
