"""Repository layer for payment data access.

Provides async database operations for querying, creating, and filtering
payment records using SQLAlchemy with eager-loading of relationships.
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.payments.models import Payment


class PaymentRepository:
    """Data access object for Payment entities.

    Encapsulates all direct database interactions for payments,
    including paginated listing, single-record lookup, date-range
    queries, and record creation. All queries eagerly load the
    student and timeline relationships.
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
        """Retrieve a paginated list of payments with optional filters."""
        q = (
            select(Payment)
            .where(Payment.school_id == school_id)
            .options(
                selectinload(Payment.student),
                selectinload(Payment.timeline),
            )
        )
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
        """Fetch a single payment by its ID with relationships loaded."""
        result = await self.session.execute(
            select(Payment)
            .where(Payment.id == payment_id)
            .options(
                selectinload(Payment.student),
                selectinload(Payment.timeline),
            )
        )
        return result.scalar_one_or_none()

    async def get_payments_in_range(
        self, school_id: str, from_date: datetime, to_date: datetime
    ) -> list[Payment]:
        """Retrieve all payments within a date range for a school."""
        result = await self.session.execute(
            select(Payment)
            .where(
                Payment.school_id == school_id,
                Payment.paid_at >= from_date,
                Payment.paid_at <= to_date,
            )
            .options(
                selectinload(Payment.student),
                selectinload(Payment.timeline),
            )
        )
        return list(result.scalars().all())

    async def create_payment(self, payment: Payment) -> Payment:
        """Persist a new payment record to the database."""
        self.session.add(payment)
        await self.session.flush()
        return payment
