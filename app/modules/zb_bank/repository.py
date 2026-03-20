"""Data-access layer for ZB Bank transactions and reconciliation runs.

Provides async CRUD operations for storing fetched bank transactions,
querying them by match status, and recording reconciliation run results.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.zb_bank.models import ZBReconciliationRun, ZBTransaction


class ZBBankRepository:
    """Repository encapsulating all database operations for ZB Bank data.

    Args:
        session: An async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Transactions ---

    async def get_transaction_by_zb_id(
        self, school_id: str, zb_id: str
    ) -> ZBTransaction | None:
        """Look up a stored transaction by its ZB Bank ID.

        Args:
            school_id: The school to scope the lookup to.
            zb_id: The ZB Bank transaction ID.

        Returns:
            The ZBTransaction if found, otherwise None.
        """
        result = await self.session.execute(
            select(ZBTransaction).where(
                ZBTransaction.school_id == school_id,
                ZBTransaction.zb_id == zb_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_transaction(self, txn: ZBTransaction) -> ZBTransaction:
        """Persist a new ZB Bank transaction record.

        Args:
            txn: The ZBTransaction instance to insert.

        Returns:
            The persisted ZBTransaction.
        """
        self.session.add(txn)
        await self.session.flush()
        return txn

    async def list_transactions(
        self,
        school_id: str,
        offset: int = 0,
        limit: int = 20,
        is_matched: bool | None = None,
    ) -> tuple[list[ZBTransaction], int]:
        """Retrieve a paginated list of ZB Bank transactions.

        Args:
            school_id: The school to scope results to.
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            is_matched: Optional filter by match status.

        Returns:
            A tuple of (list of ZBTransaction objects, total count).
        """
        q = select(ZBTransaction).where(ZBTransaction.school_id == school_id)
        count_q = select(func.count(ZBTransaction.id)).where(
            ZBTransaction.school_id == school_id
        )

        if is_matched is not None:
            q = q.where(ZBTransaction.is_matched == is_matched)
            count_q = count_q.where(ZBTransaction.is_matched == is_matched)

        total = (await self.session.execute(count_q)).scalar() or 0
        result = await self.session.execute(
            q.order_by(ZBTransaction.fetched_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def get_unmatched_transactions(
        self, school_id: str
    ) -> list[ZBTransaction]:
        """Retrieve all unmatched transactions for a school.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of ZBTransaction objects where is_matched is False.
        """
        result = await self.session.execute(
            select(ZBTransaction).where(
                ZBTransaction.school_id == school_id,
                ZBTransaction.is_matched == False,  # noqa: E712
            )
        )
        return list(result.scalars().all())

    async def update_transaction_match(
        self, txn_id: str, invoice_id: str, payment_id: str
    ) -> None:
        """Mark a transaction as matched to an invoice and payment.

        Args:
            txn_id: The internal UUID of the transaction.
            invoice_id: The matched invoice ID.
            payment_id: The created payment ID.
        """
        result = await self.session.execute(
            select(ZBTransaction).where(ZBTransaction.id == txn_id)
        )
        txn = result.scalar_one_or_none()
        if txn:
            txn.is_matched = True
            txn.matched_invoice_id = invoice_id
            txn.matched_payment_id = payment_id
            await self.session.flush()

    # --- Reconciliation Runs ---

    async def create_reconciliation_run(
        self, run: ZBReconciliationRun
    ) -> ZBReconciliationRun:
        """Persist a new reconciliation run record.

        Args:
            run: The ZBReconciliationRun instance to insert.

        Returns:
            The persisted ZBReconciliationRun.
        """
        self.session.add(run)
        await self.session.flush()
        return run

    async def list_reconciliation_runs(
        self, school_id: str, limit: int = 20
    ) -> list[ZBReconciliationRun]:
        """Retrieve recent reconciliation runs for a school.

        Args:
            school_id: The school to scope results to.
            limit: Maximum number of runs to return.

        Returns:
            A list of ZBReconciliationRun objects, newest first.
        """
        result = await self.session.execute(
            select(ZBReconciliationRun)
            .where(ZBReconciliationRun.school_id == school_id)
            .order_by(ZBReconciliationRun.started_at.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
