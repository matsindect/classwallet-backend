"""Business-logic layer for fee management.

Orchestrates fee structure CRUD, the publish workflow, bulk invoice
generation per student, and invoice listing. All mutations are logged
to the audit system.
"""

import json
import uuid
from datetime import UTC, datetime

from app.core.errors import ConflictError, NotFoundError, ValidationError
from app.modules.fees.models import FeeLineItem, FeeStructure, StudentInvoice
from app.modules.fees.repository import FeeRepository
from app.modules.fees.schemas import (
    FeeStructureResponse,
    StudentInvoiceResponse,
)
from app.modules.students.repository import StudentRepository


class FeeService:
    """Service encapsulating fee and invoice business logic.

    Args:
        repo: The fee data-access repository.
        student_repo: The student repository, used to look up students
            when generating invoices.
        audit_repo: The audit-log repository used to record mutations.
    """

    def __init__(self, repo, student_repo, audit_repo):
        self.repo: FeeRepository = repo
        self.student_repo: StudentRepository = student_repo
        self.audit_repo = audit_repo

    # ------------------------------------------------------------------
    # Fee structures
    # ------------------------------------------------------------------

    async def list_structures(self, school_id: str) -> list[dict]:
        """Return all fee structures for a school as serialised dicts.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of camelCase-serialised fee structure dicts.
        """
        structures = await self.repo.list_structures(school_id)
        return [FeeStructureResponse.from_model(s).model_dump(by_alias=True) for s in structures]

    async def create_structure(self, school_id: str, data: dict, actor_id: str) -> dict:
        """Create a new fee structure with line items and log the action.

        Args:
            school_id: The school the fee structure belongs to.
            data: Dictionary of fee structure field values (from schema).
            actor_id: ID of the user performing the action.

        Returns:
            The newly created fee structure as a camelCase-serialised dict.
        """
        grades = data.pop("grades", [])
        line_items_data = data.pop("line_items", [])

        # Calculate total amount from line items
        total_amount = sum(li["amount"] for li in line_items_data)

        structure = FeeStructure(
            school_id=school_id,
            name=data["name"],
            term=data.get("term"),
            academic_year=data.get("academic_year"),
            grades_json=json.dumps(grades) if grades else None,
            amount=total_amount,
            currency=data.get("currency", "USD"),
            due_date=data.get("due_date"),
            status="DRAFT",
            is_published=False,
            version=1,
        )

        # Create line item objects
        for li_data in line_items_data:
            item = FeeLineItem(
                fee_structure_id=structure.id,
                name=li_data["name"],
                amount=li_data["amount"],
                description=li_data.get("description"),
                is_optional=li_data.get("is_optional", False),
            )
            structure.line_items.append(item)

        structure = await self.repo.create_structure(structure)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="fee_structure",
            entity_id=structure.id,
        )
        return FeeStructureResponse.from_model(structure).model_dump(by_alias=True)

    async def update_structure(
        self, structure_id: str, data: dict, actor_id: str, school_id: str
    ) -> dict:
        """Partially update a fee structure and log the action.

        Only DRAFT structures can be updated. If ``line_items`` is provided,
        all existing line items are replaced and the total is recalculated.

        Args:
            structure_id: UUID of the fee structure to update.
            data: Dictionary of fields to update.
            actor_id: ID of the user performing the action.
            school_id: School context for audit logging.

        Returns:
            The updated fee structure as a camelCase-serialised dict.

        Raises:
            NotFoundError: If no fee structure matches *structure_id*.
            ConflictError: If the fee structure is already published.
        """
        structure = await self.repo.get_structure(structure_id)
        if not structure:
            raise NotFoundError(message="Fee structure not found")
        if structure.status == "PUBLISHED":
            raise ConflictError(message="Cannot update a published fee structure")

        # Handle grades list -> JSON string
        if "grades" in data:
            grades = data.pop("grades")
            data["grades_json"] = json.dumps(grades) if grades else None

        # Handle line items replacement
        line_items_data = data.pop("line_items", None)

        structure = await self.repo.update_structure(structure_id, data)

        if line_items_data is not None:
            new_items = [
                FeeLineItem(
                    fee_structure_id=structure_id,
                    name=li["name"],
                    amount=li["amount"],
                    description=li.get("description"),
                    is_optional=li.get("is_optional", False),
                )
                for li in line_items_data
            ]
            await self.repo.replace_line_items(structure, new_items)

            # Recalculate total
            total_amount = sum(li["amount"] for li in line_items_data)
            await self.repo.update_structure(structure_id, {"amount": total_amount})
            # Re-fetch to get updated state
            structure = await self.repo.get_structure(structure_id)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="fee_structure",
            entity_id=structure_id,
        )
        return FeeStructureResponse.from_model(structure).model_dump(by_alias=True)

    async def publish_structure(self, structure_id: str, actor_id: str, school_id: str) -> dict:
        """Publish a fee structure, making it available for invoice generation.

        Sets ``status`` to ``PUBLISHED``, ``is_published`` to ``True``,
        records ``published_at``, and increments ``version``.

        Args:
            structure_id: UUID of the fee structure to publish.
            actor_id: ID of the user performing the action.
            school_id: School context for audit logging.

        Returns:
            The published fee structure as a camelCase-serialised dict.

        Raises:
            NotFoundError: If no fee structure matches *structure_id*.
            ConflictError: If the fee structure is already published.
        """
        structure = await self.repo.get_structure(structure_id)
        if not structure:
            raise NotFoundError(message="Fee structure not found")
        if structure.status == "PUBLISHED":
            raise ConflictError(message="Fee structure is already published")

        structure = await self.repo.update_structure(
            structure_id,
            {
                "status": "PUBLISHED",
                "is_published": True,
                "published_at": datetime.now(UTC),
                "version": structure.version + 1,
            },
        )

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="publish",
            entity="fee_structure",
            entity_id=structure_id,
        )
        return FeeStructureResponse.from_model(structure).model_dump(by_alias=True)

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    async def generate_invoices(self, structure_id: str, actor_id: str, school_id: str) -> int:
        """Generate one invoice per eligible student for a fee structure.

        Uses ``grades_json`` to determine which students to invoice. If the
        fee structure has grades, only students matching those grades receive
        invoices. Falls back to the legacy ``grade`` column, then to all
        students if neither is set.

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

        # Determine target students based on grades
        grades: list[str] = []
        if structure.grades_json:
            try:
                grades = json.loads(structure.grades_json)
            except (json.JSONDecodeError, TypeError):
                grades = []

        if grades:
            students = await self.student_repo.get_students_by_grades(school_id, grades)
        elif structure.grade:
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
                status="UNPAID",
                currency=structure.currency,
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

    async def list_invoices(self, school_id: str, student_id: str | None = None) -> list[dict]:
        """Return invoices for a school with nested student/fee data.

        Args:
            school_id: The school to scope results to.
            student_id: Optional student UUID to narrow results.

        Returns:
            A list of camelCase-serialised invoice dicts with nested
            student and fee structure summaries.
        """
        invoices = await self.repo.list_invoices(school_id, student_id)

        results = []
        for inv in invoices:
            # Load related student and fee structure for nested summaries
            student = await self.student_repo.get_by_id(inv.student_id)
            fee_structure = await self.repo.get_structure(inv.fee_structure_id)

            response = StudentInvoiceResponse.from_model(
                inv, student=student, fee_structure=fee_structure
            )
            results.append(response.model_dump(by_alias=True))

        return results
