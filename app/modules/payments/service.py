"""Service layer for payment business logic.

Orchestrates payment listing, retrieval, and daily reconciliation,
delegating persistence to the PaymentRepository and cross-cutting
audit logging to the AuditRepository.
"""

from collections import defaultdict
from datetime import datetime

from app.core.errors import NotFoundError
from app.modules.audit.repository import AuditRepository
from app.modules.fees.repository import FeeRepository
from app.modules.payments.models import Payment
from app.modules.payments.repository import PaymentRepository


class PaymentService:
    """Business logic service for payment operations.

    Provides paginated listing with filters, single-payment retrieval,
    and daily reconciliation summaries grouped by payment method. All
    reconciliation actions are recorded in the audit log.

    Args:
        repo: Repository for payment data access.
        fee_repo: Repository for fee/invoice data access.
        audit_repo: Repository for writing audit log entries.
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
        """List payments with pagination and optional filters.

        Args:
            school_id: The school to scope payments to.
            page: The 1-based page number.
            page_size: Number of records per page.
            status: Optional filter by payment status.
            from_date: Optional lower bound (inclusive) on paid_at.
            to_date: Optional upper bound (inclusive) on paid_at.
            student_id: Optional filter by student identifier.

        Returns:
            A tuple of (list of Payment objects, total matching count).
        """
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

        Args:
            payment_id: The UUID of the payment to fetch.

        Returns:
            The matching Payment object.

        Raises:
            NotFoundError: If no payment with the given ID exists.
        """
        payment = await self.repo.get_payment(payment_id)
        if not payment:
            raise NotFoundError(message="Payment not found")
        return payment

    async def get_reconciliation(
        self, school_id: str, from_date: datetime, to_date: datetime
    ) -> list[dict]:
        """Generate a daily reconciliation summary for a date range.

        Aggregates payments by day and payment method, producing a sorted
        list of daily summaries. Logs a reconciliation audit event upon
        completion.

        Args:
            school_id: The school to generate the reconciliation for.
            from_date: Start of the date range (inclusive).
            to_date: End of the date range (inclusive).

        Returns:
            A list of dicts, each containing date, total_collected,
            total_payments, and a methods breakdown.
        """
        payments = await self.repo.get_payments_in_range(school_id, from_date, to_date)

        daily: dict[str, dict] = defaultdict(
            lambda: {"total_collected": 0.0, "total_payments": 0, "methods": defaultdict(float)}
        )

        for p in payments:
            day = p.paid_at.strftime("%Y-%m-%d")
            daily[day]["total_collected"] += p.amount
            daily[day]["total_payments"] += 1
            daily[day]["methods"][p.method] += p.amount

        result = []
        for date_str in sorted(daily.keys()):
            d = daily[date_str]
            result.append(
                {
                    "date": date_str,
                    "total_collected": d["total_collected"],
                    "total_payments": d["total_payments"],
                    "methods": dict(d["methods"]),
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
