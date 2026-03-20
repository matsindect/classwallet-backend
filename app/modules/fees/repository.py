"""Data-access layer for fee structures and student invoices.

Provides async CRUD operations and query methods against the
``fee_structures`` and ``student_invoices`` tables via SQLAlchemy.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.fees.models import FeeStructure, StudentInvoice


class FeeRepository:
    """Repository encapsulating all database operations for fees and invoices.

    Args:
        session: An async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_structures(self, school_id: str) -> list[FeeStructure]:
        """Return all fee structures for a school, newest first.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of ``FeeStructure`` objects ordered by descending
            ``created_at``.
        """
        result = await self.session.execute(
            select(FeeStructure)
            .where(FeeStructure.school_id == school_id)
            .order_by(FeeStructure.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_structure(self, structure_id: str) -> FeeStructure | None:
        """Fetch a single fee structure by primary key.

        Args:
            structure_id: The UUID of the fee structure.

        Returns:
            The ``FeeStructure`` if found, otherwise ``None``.
        """
        result = await self.session.execute(
            select(FeeStructure).where(FeeStructure.id == structure_id)
        )
        return result.scalar_one_or_none()

    async def create_structure(self, structure: FeeStructure) -> FeeStructure:
        """Persist a new fee structure record.

        Args:
            structure: A ``FeeStructure`` instance to insert.

        Returns:
            The same ``FeeStructure`` instance after flushing to the database.
        """
        self.session.add(structure)
        await self.session.flush()
        return structure

    async def update_structure(self, structure_id: str, data: dict) -> FeeStructure | None:
        """Apply a partial update to an existing fee structure.

        Only keys present in *data* whose values are not ``None`` are written.

        Args:
            structure_id: The UUID of the fee structure to update.
            data: Dictionary of field names to new values.

        Returns:
            The updated ``FeeStructure``, or ``None`` if not found.
        """
        result = await self.session.execute(
            select(FeeStructure).where(FeeStructure.id == structure_id)
        )
        structure = result.scalar_one_or_none()
        if not structure:
            return None
        for key, value in data.items():
            if hasattr(structure, key) and value is not None:
                setattr(structure, key, value)
        await self.session.flush()
        return structure

    async def create_invoice(self, invoice: StudentInvoice) -> StudentInvoice:
        """Persist a new student invoice record.

        Args:
            invoice: A ``StudentInvoice`` instance to insert.

        Returns:
            The same ``StudentInvoice`` instance after flushing.
        """
        self.session.add(invoice)
        await self.session.flush()
        return invoice

    async def list_invoices(
        self, school_id: str, student_id: str | None = None
    ) -> list[StudentInvoice]:
        """Return invoices for a school, optionally filtered by student.

        Args:
            school_id: The school to scope results to.
            student_id: Optional student UUID to filter invoices for a
                single student.

        Returns:
            A list of ``StudentInvoice`` objects ordered by descending
            ``created_at``.
        """
        q = select(StudentInvoice).where(StudentInvoice.school_id == school_id)
        if student_id:
            q = q.where(StudentInvoice.student_id == student_id)
        q = q.order_by(StudentInvoice.created_at.desc())
        result = await self.session.execute(q)
        return list(result.scalars().all())

    async def get_invoice(self, invoice_id: str) -> StudentInvoice | None:
        """Fetch a single invoice by primary key.

        Args:
            invoice_id: The UUID of the invoice.

        Returns:
            The ``StudentInvoice`` if found, otherwise ``None``.
        """
        result = await self.session.execute(
            select(StudentInvoice).where(StudentInvoice.id == invoice_id)
        )
        return result.scalar_one_or_none()

    async def get_outstanding_invoices(self, school_id: str) -> list[StudentInvoice]:
        """Return all invoices with an outstanding balance for a school.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of ``StudentInvoice`` objects where ``balance > 0``.
        """
        result = await self.session.execute(
            select(StudentInvoice).where(
                StudentInvoice.school_id == school_id,
                StudentInvoice.balance > 0,
            )
        )
        return list(result.scalars().all())
