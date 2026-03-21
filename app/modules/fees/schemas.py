"""Pydantic schemas for fee structure and invoice request/response handling.

All schemas inherit from ``CamelModel`` for automatic camelCase serialisation.
Provides input schemas for creating and updating fee structures, as well as
response schemas for fee structures, student invoices, and invoice
generation results.
"""

import json
from datetime import datetime

from app.core.schemas import CamelModel

# ---------------------------------------------------------------------------
# Fee Line Items
# ---------------------------------------------------------------------------


class FeeLineItemCreate(CamelModel):
    """Schema for creating a line item within a fee structure."""

    name: str
    amount: float
    description: str | None = None
    is_optional: bool = False


class FeeLineItemResponse(CamelModel):
    """Response schema for a fee line item."""

    id: str
    name: str
    amount: float
    description: str | None = None
    is_optional: bool


# ---------------------------------------------------------------------------
# Fee Structures
# ---------------------------------------------------------------------------


class FeeStructureCreate(CamelModel):
    """Schema for creating a new fee structure.

    Attributes:
        name: Name of the fee structure.
        term: Term label (e.g. "First Term").
        academic_year: Academic year label (e.g. "2024").
        grades: List of grade strings this fee applies to.
        line_items: Breakdown of individual charges.
        due_date: Due date string in YYYY-MM-DD format.
    """

    name: str
    term: str
    academic_year: str
    grades: list[str]
    line_items: list[FeeLineItemCreate]
    due_date: str


class FeeStructureUpdate(CamelModel):
    """Schema for partially updating an existing fee structure.

    All fields are optional; only fields that are explicitly set
    (``exclude_unset=True``) will be applied to the record.
    """

    name: str | None = None
    term: str | None = None
    academic_year: str | None = None
    grades: list[str] | None = None
    line_items: list[FeeLineItemCreate] | None = None
    due_date: str | None = None


class FeeStructureResponse(CamelModel):
    """Response schema returned when reading a fee structure.

    ``grades`` is parsed from the model's ``grades_json`` text column.
    ``total_amount`` is the sum of line item amounts (or the stored amount).
    """

    id: str
    name: str
    term: str | None = None
    academic_year: str | None = None
    grades: list[str] = []
    line_items: list[FeeLineItemResponse] = []
    total_amount: float
    currency: str
    due_date: str | None = None
    status: str
    version: int
    created_at: datetime
    published_at: datetime | None = None

    @classmethod
    def from_model(cls, model: object) -> "FeeStructureResponse":
        """Build a response from a ``FeeStructure`` ORM instance.

        Parses ``grades_json`` into a Python list, maps ``amount`` to
        ``total_amount``, and converts line items eagerly.
        """
        grades: list[str] = []
        if getattr(model, "grades_json", None):
            try:
                grades = json.loads(model.grades_json)
            except (json.JSONDecodeError, TypeError):
                grades = []

        line_items_raw = getattr(model, "line_items", []) or []
        line_items = [
            FeeLineItemResponse(
                id=li.id,
                name=li.name,
                amount=li.amount,
                description=li.description,
                is_optional=li.is_optional,
            )
            for li in line_items_raw
        ]

        return cls(
            id=model.id,
            name=model.name,
            term=model.term,
            academic_year=model.academic_year,
            grades=grades,
            line_items=line_items,
            total_amount=model.amount,
            currency=model.currency,
            due_date=model.due_date,
            status=model.status,
            version=model.version,
            created_at=model.created_at,
            published_at=model.published_at,
        )


# ---------------------------------------------------------------------------
# Invoice nested summaries
# ---------------------------------------------------------------------------


class InvoiceStudentSummary(CamelModel):
    """Nested student summary included in invoice responses."""

    first_name: str
    last_name: str
    student_id: str | None = None
    grade: str | None = None
    class_name: str | None = None


class InvoiceFeeStructureSummary(CamelModel):
    """Nested fee structure summary included in invoice responses."""

    name: str
    term: str | None = None
    academic_year: str | None = None


# ---------------------------------------------------------------------------
# Invoices
# ---------------------------------------------------------------------------


class StudentInvoiceResponse(CamelModel):
    """Response schema for a student invoice.

    Maps model fields to the API contract naming:
    - ``amount`` -> ``totalAmount``
    - ``amount_paid`` -> ``paidAmount``
    """

    id: str
    student_id: str
    student: InvoiceStudentSummary | None = None
    fee_structure_id: str
    fee_structure: InvoiceFeeStructureSummary | None = None
    total_amount: float
    paid_amount: float
    balance: float
    currency: str
    due_date: str | None = None
    status: str
    created_at: datetime

    @classmethod
    def from_model(
        cls,
        model: object,
        student: object | None = None,
        fee_structure: object | None = None,
    ) -> "StudentInvoiceResponse":
        """Build a response from a ``StudentInvoice`` ORM instance.

        Optionally populates nested ``student`` and ``fee_structure``
        summary objects when the related models are provided.
        """
        student_summary = None
        if student is not None:
            student_summary = InvoiceStudentSummary(
                first_name=student.first_name,
                last_name=student.last_name,
                student_id=student.student_id,
                grade=student.grade,
                class_name=student.class_name,
            )

        fee_summary = None
        if fee_structure is not None:
            fee_summary = InvoiceFeeStructureSummary(
                name=fee_structure.name,
                term=fee_structure.term,
                academic_year=fee_structure.academic_year,
            )

        return cls(
            id=model.id,
            student_id=model.student_id,
            student=student_summary,
            fee_structure_id=model.fee_structure_id,
            fee_structure=fee_summary,
            total_amount=model.amount,
            paid_amount=model.amount_paid,
            balance=model.balance,
            currency=getattr(model, "currency", "USD"),
            due_date=model.due_date,
            status=model.status,
            created_at=model.created_at,
        )


class InvoiceGenerationResponse(CamelModel):
    """Response schema returned after bulk invoice generation.

    Attributes:
        count: The number of invoices that were created.
    """

    count: int
