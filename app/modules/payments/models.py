"""SQLAlchemy models for the payments module.

Defines the Payment ORM model representing financial transactions
recorded against student invoices within a school.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Payment(Base):
    """Represents a single payment transaction.

    Each payment is linked to a school, student, and invoice. It records the
    amount paid, payment method, status, and an optional reference or notes
    field. Timestamps track when the payment was made and when the record
    was created or last updated.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the school this payment belongs to.
        student_id: Foreign key to the student who made the payment.
        invoice_id: Foreign key to the invoice being paid.
        amount: The monetary amount of the payment.
        method: Payment method (e.g., "cash", "card", "bank_transfer").
        reference: Optional external reference number or identifier.
        status: Current status of the payment (default "completed").
        notes: Optional free-text notes about the payment.
        paid_at: Timestamp when the payment was made.
        created_by: Foreign key to the user who recorded the payment.
        created_at: Timestamp when the record was created.
        updated_at: Timestamp when the record was last updated.
    """
    __tablename__ = "payments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    invoice_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("student_invoices.id"), nullable=False
    )
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    method: Mapped[str] = mapped_column(String(50), default="cash")
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
