"""SQLAlchemy models for the ZB Bank integration module.

Defines ORM models for storing raw bank transaction data fetched from the
ZB Bank API and tracking reconciliation runs that match those transactions
to internal student invoices.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ZBTransaction(Base):
    """A raw payment transaction fetched from the ZB Bank API.

    Stores the complete payload returned by the ``/alerts/payments/all-payments``
    or ``/alerts/payments/pick-all-pending`` endpoints. Once reconciled, the
    ``is_matched`` flag is set and the matching invoice/payment IDs are recorded.

    Attributes:
        id: Internal UUID primary key.
        school_id: Foreign key to the school this transaction belongs to.
        zb_id: The transaction ID from ZB Bank (``id`` field in the API response).
        amount: Transaction amount.
        date: Date string as returned by ZB Bank.
        transaction_date: Full transaction datetime as returned by ZB Bank.
        narrative: Free-text narrative describing the payment.
        reference: Bank reference identifier.
        source: Payment source channel.
        status: ZB Bank transaction status.
        nr1: Narrative field 1 (often contains student/invoice reference).
        nr2: Narrative field 2.
        nr3: Narrative field 3.
        nr4: Narrative field 4.
        picked: Whether the transaction has been picked/acknowledged by ZB Bank.
        tcd: Transaction code from ZB Bank.
        is_matched: Whether this transaction has been matched to an invoice.
        matched_invoice_id: Foreign key to the matched invoice, if any.
        matched_payment_id: Foreign key to the created Payment record, if any.
        fetched_at: Timestamp when this record was fetched from ZB Bank.
    """

    __tablename__ = "zb_transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    zb_id: Mapped[str] = mapped_column(String(100), nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    transaction_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    narrative: Mapped[str | None] = mapped_column(Text, nullable=True)
    reference: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str | None] = mapped_column(String(50), nullable=True)
    nr1: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nr2: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nr3: Mapped[str | None] = mapped_column(String(255), nullable=True)
    nr4: Mapped[str | None] = mapped_column(String(255), nullable=True)
    picked: Mapped[str | None] = mapped_column(String(50), nullable=True)
    tcd: Mapped[str | None] = mapped_column(String(50), nullable=True)
    is_matched: Mapped[bool] = mapped_column(Boolean, default=False)
    matched_invoice_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("student_invoices.id"), nullable=True
    )
    matched_payment_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("payments.id"), nullable=True
    )
    fetched_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class ZBReconciliationRun(Base):
    """Tracks a single reconciliation run between ZB Bank data and invoices.

    Each run records counts of matched, unmatched, and skipped (duplicate)
    transactions, along with the total amount successfully reconciled.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the school.
        started_at: When the reconciliation run began.
        completed_at: When the reconciliation run finished.
        total_transactions: Number of bank transactions processed.
        matched_count: Number of transactions matched to invoices.
        unmatched_count: Number of transactions that could not be matched.
        skipped_count: Number of transactions skipped (already matched).
        total_amount_reconciled: Sum of matched transaction amounts.
        status: Run status (e.g. "completed", "failed").
        error_details: Optional error message if the run failed.
    """

    __tablename__ = "zb_reconciliation_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    total_transactions: Mapped[int] = mapped_column(Integer, default=0)
    matched_count: Mapped[int] = mapped_column(Integer, default=0)
    unmatched_count: Mapped[int] = mapped_column(Integer, default=0)
    skipped_count: Mapped[int] = mapped_column(Integer, default=0)
    total_amount_reconciled: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    error_details: Mapped[str | None] = mapped_column(Text, nullable=True)
