"""SQLAlchemy models for the fees module.

Defines the ``FeeStructure``, ``FeeLineItem``, and ``StudentInvoice`` ORM
models that map to the ``fee_structures``, ``fee_line_items``, and
``student_invoices`` database tables respectively.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class FeeLineItem(Base):
    """An individual line item within a fee structure.

    Represents a single charge component (e.g. "Tuition Fee", "Sports Fee")
    that contributes to the total amount of a fee structure.

    Attributes:
        id: UUID primary key.
        fee_structure_id: Foreign key referencing the parent fee structure.
        name: Name of the line item (e.g. "Tuition Fee").
        amount: The charge amount for this line item.
        description: Optional description of the charge.
        is_optional: Whether this line item is optional for students.
    """

    __tablename__ = "fee_line_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fee_structure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fee_structures.id"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)


class FeeStructure(Base):
    """Defines a fee that can be charged to students.

    A fee structure belongs to a school and optionally targets specific
    grades (stored as a JSON array in ``grades_json``). It must be published
    before invoices can be generated from it.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key referencing the owning school.
        name: Human-readable name for the fee (e.g. "Tuition Term 1").
        description: Optional longer description.
        grade: Legacy single-grade column, kept for backward compatibility.
        grades_json: JSON-encoded list of grade strings (e.g. '["Form 4", "Form 5"]').
        amount: The total fee amount (sum of line items).
        currency: ISO currency code, defaults to "USD".
        academic_year: Optional academic year label (e.g. "2025-2026").
        term: Optional term/semester label.
        due_date: Optional due-date string for generated invoices.
        is_published: Whether the structure has been published.
        status: Workflow status — "DRAFT" or "PUBLISHED".
        version: Version counter, incremented on publish.
        published_at: Timestamp when the structure was published.
        created_at: Timestamp of record creation (UTC).
        updated_at: Timestamp of last update (UTC), auto-updated on change.
        line_items: Related ``FeeLineItem`` objects.
    """

    __tablename__ = "fee_structures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    grade: Mapped[str | None] = mapped_column(String(50), nullable=True)
    grades_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    academic_year: Mapped[str | None] = mapped_column(String(20), nullable=True)
    term: Mapped[str | None] = mapped_column(String(50), nullable=True)
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(20), default="DRAFT")
    version: Mapped[int] = mapped_column(Integer, default=1)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    line_items = relationship(
        "FeeLineItem", backref="fee_structure", cascade="all, delete-orphan", lazy="selectin"
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
        invoice_number: Unique human-readable invoice identifier.
        amount: Total invoiced amount.
        amount_paid: Amount paid so far, defaults to 0.
        balance: Outstanding balance (amount - amount_paid).
        status: Payment status, defaults to "UNPAID".
        currency: ISO currency code, defaults to "USD".
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
    status: Mapped[str] = mapped_column(String(20), default="UNPAID")
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    due_date: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )
