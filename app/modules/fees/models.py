"""SQLAlchemy models for the fees module.

Defines the ``FeeStructure`` and ``StudentInvoice`` ORM models that map to
the ``fee_structures`` and ``student_invoices`` database tables respectively.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class FeeStructure(Base):
    """Defines a fee that can be charged to students.

    A fee structure belongs to a school and optionally targets a specific
    grade. It must be published before invoices can be generated from it.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the owning school.
        name: Human-readable name for the fee (e.g. "Tuition Term 1").
        description: Optional longer description.
        grade: Optional grade filter; when set, invoices are generated
            only for students in this grade.
        amount: The fee amount.
        currency: ISO currency code, defaults to "USD".
        academic_year: Optional academic year label (e.g. "2025-2026").
        term: Optional term/semester label.
        due_date: Optional due-date string for generated invoices.
        is_published: Whether the structure has been published and is
            available for invoice generation.
        created_at: Timestamp of record creation (UTC).
        updated_at: Timestamp of last update (UTC), auto-updated on change.
    """

    __tablename__ = "fee_structures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class StudentInvoice(Base):
    """An invoice issued to an individual student for a specific fee structure.

    One invoice is created per student when invoices are generated from a
    published ``FeeStructure``. Tracks the total amount, amount paid,
    remaining balance, and payment status.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the school.
        student_id: Foreign key referencing the invoiced student.
        fee_structure_id: Foreign key referencing the originating fee structure.
        invoice_number: Unique human-readable invoice identifier (e.g.
            "INV-A1B2C3D4").
        amount: Total invoiced amount.
        amount_paid: Amount paid so far, defaults to 0.
        balance: Outstanding balance (amount - amount_paid).
        status: Payment status, defaults to "unpaid".
        due_date: Optional due-date string inherited from the fee structure.
        created_at: Timestamp of record creation (UTC).
        updated_at: Timestamp of last update (UTC), auto-updated on change.
    """

    __tablename__ = "student_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    fee_structure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fee_structures.id"), nullable=False
    )
    invoice_number: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    amount_paid: Mapped[float] = mapped_column(Float, default=0.0)
    balance: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="unpaid")
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
