"""Service layer for payment business logic.

Orchestrates payment listing, retrieval, creation, and daily reconciliation,
delegating persistence to the PaymentRepository and cross-cutting
audit logging to the AuditRepository.
"""

import random
import string
from collections import defaultdict
from datetime import UTC, datetime

from app.core.errors import NotFoundError
from app.modules.audit.repository import AuditRepository
from app.modules.fees.repository import FeeRepository
from app.modules.payments.models import Payment, PaymentTimeline
from app.modules.payments.repository import PaymentRepository


def _generate_receipt_number() -> str:
    """Generate a receipt number in the format RCP-YYYY-XXXXXX."""
    year = datetime.now(UTC).strftime("%Y")
    suffix = "".join(random.choices(string.digits, k=6))
    return f"RCP-{year}-{suffix}"


class PaymentService:
    """Business logic service for payment operations.

    Provides paginated listing with filters, single-payment retrieval,
    payment creation with receipt generation and timeline tracking,
    and daily reconciliation summaries. All reconciliation actions are
    recorded in the audit log.
    """

    def __init__(
        self,
        repo: PaymentRepository,
        fee_repo: FeeRepository,
        audit_repo: AuditRepository,
    ):
        self.repo = repo
        self.fee_repo = fee_repo
        self.audit_repo = audit_repo

    async def list_payments(
        self,
        school_id: str,
        page: int,
        page_size: int,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        student_id: str | None = None,
    ) -> tuple[list[Payment], int]:
        """List payments with pagination and optional filters."""
        offset = (page - 1) * page_size
        return await self.repo.list_payments(
            school_id=school_id,
            offset=offset,
            limit=page_size,
            status=status,
            from_date=from_date,
            to_date=to_date,
            student_id=student_id,
        )

    async def get_payment(self, payment_id: str) -> Payment:
        """Retrieve a single payment by ID.

        Raises:
            NotFoundError: If no payment with the given ID exists.
        """
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise NotFoundError(message="Payment not found")
        return payment

    async def create_payment(
        self,
        payment: Payment,
    ) -> Payment:
        """Create a new payment with receipt number and initial timeline entry.

        Generates a receipt number if not already set, resolves the channel
        from the method field when not provided, and creates an initial
        'Payment Initiated' timeline entry.
        """
        # Generate receipt number
        if not payment.receipt_number:
            payment.receipt_number = _generate_receipt_number()

        # Set channel from method if not provided
        if not payment.channel:
            payment.channel = payment.method

        # Create initial timeline entry
        initial_event = PaymentTimeline(
            payment_id=payment.id,
            event="Payment Initiated",
            description=f"{payment.channel or payment.method} payment initiated",
        )
        payment.timeline.append(initial_event)

        created = await self.repo.create_payment(payment)
        return created

    async def update_payment_status(
        self,
        payment_id: str,
        new_status: str,
        description: str | None = None,
    ) -> Payment:
        """Update a payment's status and add a timeline entry.

        Args:
            payment_id: The UUID of the payment to update.
            new_status: The new status value.
            description: Optional description for the timeline event.

        Raises:
            NotFoundError: If no payment with the given ID exists.
        """
        payment = await self.get_payment(payment_id)
        old_status = payment.status
        payment.status = new_status
        payment.updated_at = datetime.now(UTC)

        # Add timeline entry for status change
        status_event = PaymentTimeline(
            payment_id=payment.id,
            event=f"Status changed to {new_status}",
            description=description or f"Payment status changed from {old_status} to {new_status}",
        )
        payment.timeline.append(status_event)

        await self.repo.session.flush()
        return payment

    async def get_reconciliation(
        self, school_id: str, from_date: datetime, to_date: datetime
    ) -> list[dict]:
        """Generate a daily reconciliation summary for a date range.

        Aggregates payments by day, producing sorted daily summaries that
        match the frontend contract with transaction counts by status.
        """
        payments = await self.repo.get_payments_in_range(school_id, from_date, to_date)

        daily: dict[str, dict] = defaultdict(
            lambda: {
                "total_transactions": 0,
                "success_count": 0,
                "failed_count": 0,
                "pending_count": 0,
                "total_amount": 0.0,
                "success_amount": 0.0,
                "unmatched_payments": 0,
            }
        )

        for p in payments:
            day = p.paid_at.strftime("%Y-%m-%d")
            daily[day]["total_transactions"] += 1
            daily[day]["total_amount"] += p.amount

            status_lower = (p.status or "").lower()
            if status_lower in ("success", "completed"):
                daily[day]["success_count"] += 1
                daily[day]["success_amount"] += p.amount
            elif status_lower == "failed":
                daily[day]["failed_count"] += 1
            elif status_lower == "pending":
                daily[day]["pending_count"] += 1

        result = []
        for date_str in sorted(daily.keys()):
            d = daily[date_str]
            total = d["total_transactions"]
            success_rate = round((d["success_count"] / total) * 100, 1) if total > 0 else 0.0
            result.append(
                {
                    "date": date_str,
                    "total_transactions": total,
                    "success_count": d["success_count"],
                    "failed_count": d["failed_count"],
                    "pending_count": d["pending_count"],
                    "total_amount": d["total_amount"],
                    "success_amount": d["success_amount"],
                    "success_rate": success_rate,
                    "unmatched_payments": d["unmatched_payments"],
                }
            )

        await self.audit_repo.log(
            school_id=school_id,
            actor_id="system",
            action="reconciliation",
            entity="payment",
            metadata={"from": from_date.isoformat(), "to": to_date.isoformat()},
        )
        return result
