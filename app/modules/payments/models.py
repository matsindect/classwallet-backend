"""SQLAlchemy models for the payments module.

Defines the Payment and PaymentTimeline ORM models representing financial
transactions recorded against student invoices within a school.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Payment(Base):
    """Represents a single payment transaction.

    Each payment is linked to a school, student, and invoice. It records the
    amount paid, payment method/channel, status, payer details, and an optional
    reference or notes field. Timestamps track when the payment was made and
    when the record was created or last updated.
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
    channel: Mapped[str | None] = mapped_column(String(50), nullable=True)
    provider: Mapped[str | None] = mapped_column(String(100), nullable=True)
    payer_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    payer_phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    payer_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    receipt_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="completed")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    paid_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    # Relationships
    student = relationship("Student", lazy="selectin")
    timeline = relationship(
        "PaymentTimeline",
        backref="payment",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PaymentTimeline.timestamp",
    )


class PaymentTimeline(Base):
    """Represents a timeline event for a payment."""

    __tablename__ = "payment_timeline"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    payment_id: Mapped[str] = mapped_column(String(36), ForeignKey("payments.id"), nullable=False)
    event: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
