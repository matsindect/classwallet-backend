"""Pydantic schemas for the payments module.

Defines request/response models for payment-related API endpoints,
including payment details and daily reconciliation summaries.
"""

from datetime import datetime

from pydantic import BaseModel


class PaymentResponse(BaseModel):
    """Response schema for a single payment record.

    Serializes a Payment ORM model into a JSON-compatible representation
    for API responses. Configured with ``from_attributes`` to support
    direct construction from SQLAlchemy model instances.

    Attributes:
        id: Unique identifier for the payment.
        school_id: Identifier of the school the payment belongs to.
        student_id: Identifier of the student who made the payment.
        invoice_id: Identifier of the invoice being paid.
        amount: Monetary amount of the payment.
        method: Payment method used (e.g., "cash").
        reference: Optional external reference string.
        status: Current status of the payment.
        notes: Optional free-text notes.
        paid_at: When the payment was made.
        created_by: Identifier of the user who recorded the payment.
        created_at: When the record was created.
        updated_at: When the record was last modified.
    """
    id: str
    school_id: str
    student_id: str
    invoice_id: str
    amount: float
    method: str
    reference: str | None = None
    status: str
    notes: str | None = None
    paid_at: datetime
    created_by: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReconciliationSummary(BaseModel):
    """Response schema for a daily reconciliation summary.

    Aggregates payment data for a single day, breaking down totals
    by payment method.

    Attributes:
        date: The date string (YYYY-MM-DD) the summary covers.
        total_collected: Sum of all payment amounts for the day.
        total_payments: Count of payments recorded on the day.
        methods: Mapping of payment method names to their collected totals.
    """

    date: str
    total_collected: float
    total_payments: int
    methods: dict[str, float]
