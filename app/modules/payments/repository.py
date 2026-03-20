"""Repository layer for payment data access.

Provides async database operations for querying, creating, and filtering
payment records using SQLAlchemy.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payments.models import Payment


class PaymentRepository:
    """Data access object for Payment entities.

    Encapsulates all direct database interactions for payments,
    including paginated listing, single-record lookup, date-range
    queries, and record creation.

    Args:
        session: An async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_payments(
        self,
        school_id: str,
        offset: int = 0,
        limit: int = 20,
        status: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        student_id: str | None = None,
    ) -> tuple[list[Payment], int]:
        """Retrieve a paginated list of payments with optional filters.

        Args:
            school_id: The school to scope payments to.
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            status: Optional filter by payment status.
            from_date: Optional lower bound (inclusive) on paid_at.
            to_date: Optional upper bound (inclusive) on paid_at.
            student_id: Optional filter by student identifier.

        Returns:
            A tuple of (list of Payment objects, total matching count).
        """
        q = select(Payment).where(Payment.school_id == school_id)
        count_q = select(func.count(Payment.id)).where(Payment.school_id == school_id)

        if status:
            q = q.where(Payment.status == status)
            count_q = count_q.where(Payment.status == status)
        if from_date:
            q = q.where(Payment.paid_at >= from_date)
            count_q = count_q.where(Payment.paid_at >= from_date)
        if to_date:
            q = q.where(Payment.paid_at <= to_date)
            count_q = count_q.where(Payment.paid_at <= to_date)
        if student_id:
            q = q.where(Payment.student_id == student_id)
            count_q = count_q.where(Payment.student_id == student_id)

        total = (await self.session.execute(count_q)).scalar() or 0
        result = await self.session.execute(
            q.order_by(Payment.paid_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_payment(self, payment_id: str) -> Payment | None:
        """Fetch a single payment by its ID.

        Args:
            payment_id: The UUID of the payment to retrieve.

        Returns:
            The Payment object if found, or None.
        """
        result = await self.session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    async def get_payments_in_range(
        self, school_id: str, from_date: datetime, to_date: datetime
    ) -> list[Payment]:
        """Retrieve all payments within a date range for a school.

        Args:
            school_id: The school to scope payments to.
            from_date: Start of the date range (inclusive).
            to_date: End of the date range (inclusive).

        Returns:
            A list of Payment objects falling within the specified range.
        """
        result = await self.session.execute(
            select(Payment).where(
                Payment.school_id == school_id,
                Payment.paid_at >= from_date,
                Payment.paid_at <= to_date,
            )
        )
        return list(result.scalars().all())

    async def create_payment(self, payment: Payment) -> Payment:
        """Persist a new payment record to the database.

        Args:
            payment: The Payment model instance to insert.

        Returns:
            The persisted Payment object (with generated ID).
        """
        self.session.add(payment)
        await self.session.flush()
        return payment
