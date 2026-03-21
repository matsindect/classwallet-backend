"""Pydantic schemas for the payments module.

Defines request/response models for payment-related API endpoints,
using CamelModel for camelCase serialisation to match the frontend contract.
"""

from __future__ import annotations

import json
from datetime import datetime

from app.core.schemas import CamelModel


class PaymentTimelineResponse(CamelModel):
    """Response schema for a single payment timeline event."""

    id: str
    event: str
    description: str | None = None
    timestamp: datetime


class PaymentStudentSummary(CamelModel):
    """Nested student summary embedded inside a payment response."""

    first_name: str
    last_name: str
    student_id: str
    grade: str | None = None


class PaymentResponse(CamelModel):
    """Response schema for a single payment record."""

    id: str
    reference: str | None = None
    student_id: str
    student: PaymentStudentSummary | None = None
    amount: float
    currency: str = "USD"
    status: str
    channel: str | None = None
    provider: str | None = None
    payer_name: str | None = None
    payer_phone: str | None = None
    payer_email: str | None = None
    receipt_number: str | None = None
    metadata: dict | None = None
    timeline: list[PaymentTimelineResponse] = []
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, payment) -> PaymentResponse:
        """Build a PaymentResponse from a Payment ORM model instance.

        Handles mapping of legacy ``method`` to ``channel`` when channel is
        not set, parsing ``metadata_json`` into a dict, and embedding the
        student summary if the student relationship is loaded.
        """
        # Resolve channel: prefer explicit channel, fall back to method
        channel = payment.channel if payment.channel else payment.method

        # Parse metadata_json
        metadata = None
        if payment.metadata_json:
            try:
                metadata = json.loads(payment.metadata_json)
            except (json.JSONDecodeError, TypeError):
                metadata = None

        # Build student summary if relationship is loaded
        student_summary = None
        if hasattr(payment, "student") and payment.student is not None:
            student_summary = PaymentStudentSummary(
                first_name=payment.student.first_name,
                last_name=payment.student.last_name,
                student_id=payment.student.student_id or "",
                grade=getattr(payment.student, "grade", None),
            )

        # Build timeline
        timeline_items = []
        if hasattr(payment, "timeline") and payment.timeline:
            timeline_items = [
                PaymentTimelineResponse(
                    id=tl.id,
                    event=tl.event,
                    description=tl.description,
                    timestamp=tl.timestamp,
                )
                for tl in payment.timeline
            ]

        return cls(
            id=payment.id,
            reference=payment.reference,
            student_id=payment.student_id,
            student=student_summary,
            amount=payment.amount,
            currency=getattr(payment, "currency", "USD"),
            status=payment.status,
            channel=channel,
            provider=getattr(payment, "provider", None),
            payer_name=getattr(payment, "payer_name", None),
            payer_phone=getattr(payment, "payer_phone", None),
            payer_email=getattr(payment, "payer_email", None),
            receipt_number=getattr(payment, "receipt_number", None),
            metadata=metadata,
            timeline=timeline_items,
            created_at=payment.created_at,
            updated_at=payment.updated_at,
        )


class PaymentCreate(CamelModel):
    """Request schema for creating a payment."""

    student_id: str
    invoice_id: str
    amount: float
    method: str = "cash"
    channel: str | None = None
    reference: str | None = None
    notes: str | None = None


class ReconciliationSummary(CamelModel):
    """Response schema for a daily reconciliation summary.

    Matches the frontend contract with per-day transaction breakdowns.
    """

    date: str
    total_transactions: int = 0
    success_count: int = 0
    failed_count: int = 0
    pending_count: int = 0
    total_amount: float = 0.0
    success_amount: float = 0.0
    success_rate: float = 0.0
    unmatched_payments: int = 0
