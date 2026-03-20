"""Business-logic layer for fee management.

Orchestrates fee structure CRUD, the publish workflow, bulk invoice
generation per student, and invoice listing. All mutations are logged
to the audit system.
"""

import uuid

from app.core.errors import NotFoundError, ValidationError
from app.modules.audit.repository import AuditRepository
from app.modules.fees.models import FeeStructure, StudentInvoice
from app.modules.fees.repository import FeeRepository
from app.modules.students.repository import StudentRepository


class FeeService:
    """Service encapsulating fee and invoice business logic.

    Args:
        repo: The fee data-access repository.
        student_repo: The student repository, used to look up students
            when generating invoices.
        audit_repo: The audit-log repository used to record mutations.
    """

    def __init__(
        self,
        repo: FeeRepository,
        student_repo: StudentRepository,
        audit_repo: AuditRepository,
    ):
        self.repo = repo
        self.student_repo = student_repo
        self.audit_repo = audit_repo

    async def list_structures(self, school_id: str) -> list[FeeStructure]:
        """Return all fee structures for a school.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of ``FeeStructure`` objects.
        """
        return await self.repo.list_structures(school_id)

    async def create_structure(self, school_id: str, data: dict, actor_id: str) -> FeeStructure:
        """Create a new fee structure and log the action.

        Args:
            school_id: The school the fee structure belongs to.
            data: Dictionary of fee structure field values.
            actor_id: ID of the user performing the action.

        Returns:
            The newly created ``FeeStructure`` instance.
        """
        structure = FeeStructure(school_id=school_id, **data)
        structure = await self.repo.create_structure(structure)
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="fee_structure",
            entity_id=structure.id,
        )
        return structure

    async def update_structure(
        self, structure_id: str, data: dict, actor_id: str, school_id: str
    ) -> FeeStructure:
        """Partially update a fee structure and log the action.

        Args:
            structure_id: UUID of the fee structure to update.
            data: Dictionary of fields to update.
            actor_id: ID of the user performing the action.
            school_id: School context for audit logging.

        Returns:
            The updated ``FeeStructure`` instance.

        Raises:
            NotFoundError: If no fee structure matches *structure_id*.
        """
        structure = await self.repo.update_structure(structure_id, data)
        if not structure:
            raise NotFoundError(message="Fee structure not found")
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="fee_structure",
            entity_id=structure_id,
        )
        return structure

    async def publish_structure(
        self, structure_id: str, actor_id: str, school_id: str
    ) -> FeeStructure:
        """Mark a fee structure as published and log the action.

        Publishing is a prerequisite for generating invoices from the
        structure.

        Args:
            structure_id: UUID of the fee structure to publish.
            actor_id: ID of the user performing the action.
            school_id: School context for audit logging.

        Returns:
            The updated ``FeeStructure`` with ``is_published=True``.

        Raises:
            NotFoundError: If no fee structure matches *structure_id*.
        """
        structure = await self.repo.get_structure(structure_id)
        if not structure:
            raise NotFoundError(message="Fee structure not found")
        structure = await self.repo.update_structure(structure_id, {"is_published": True})
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="publish",
            entity="fee_structure",
            entity_id=structure_id,
        )
        return structure

    async def generate_invoices(self, structure_id: str, actor_id: str, school_id: str) -> int:
        """Generate one invoice per eligible student for a fee structure.

        If the fee structure specifies a grade, only students in that grade
        receive invoices. Otherwise, all students in the school are invoiced.
        Each invoice is assigned a unique invoice number (``INV-<hex>``).

        Args:
            structure_id: UUID of the published fee structure.
            actor_id: ID of the user performing the action.
            school_id: The school context.

        Returns:
            The number of invoices created.

        Raises:
            NotFoundError: If no fee structure matches *structure_id*.
            ValidationError: If the fee structure has not been published.
        """
        structure = await self.repo.get_structure(structure_id)
        if not structure:
            raise NotFoundError(message="Fee structure not found")
        if not structure.is_published:
            raise ValidationError(
                message="Fee structure must be published before generating invoices"
            )

        if structure.grade:
            students = await self.student_repo.get_students_by_grade(school_id, structure.grade)
        else:
            students = await self.student_repo.get_all_students(school_id)

        count = 0
        for student in students:
            inv_number = f"INV-{uuid.uuid4().hex[:8].upper()}"
            invoice = StudentInvoice(
                school_id=school_id,
                student_id=student.id,
                fee_structure_id=structure.id,
                invoice_number=inv_number,
                amount=structure.amount,
                amount_paid=0.0,
                balance=structure.amount,
                status="unpaid",
                due_date=structure.due_date,
            )
            await self.repo.create_invoice(invoice)
            count += 1

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="generate_invoices",
            entity="fee_structure",
            entity_id=structure_id,
            metadata={"count": count},
        )
        return count

    async def list_invoices(
        self, school_id: str, student_id: str | None = None
    ) -> list[StudentInvoice]:
        """Return invoices for a school, optionally filtered by student.

        Args:
            school_id: The school to scope results to.
            student_id: Optional student UUID to narrow results.

        Returns:
            A list of ``StudentInvoice`` objects.
        """
        return await self.repo.list_invoices(school_id, student_id)
