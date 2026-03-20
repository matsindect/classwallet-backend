"""Pydantic schemas for fee structure and invoice request/response handling.

Provides input schemas for creating and updating fee structures, as well as
response schemas for fee structures, student invoices, and invoice
generation results.
"""

from datetime import datetime

from pydantic import BaseModel


class FeeStructureCreate(BaseModel):
    """Schema for creating a new fee structure.

    All fields are optional so the caller can supply only the known
    attributes; ``school_id`` is inferred from the authenticated user.

    Attributes:
        name: Name of the fee structure.
        description: Optional description.
        grade: Optional grade to target.
        amount: Fee amount.
        currency: ISO currency code.
        academic_year: Optional academic year label.
        term: Optional term label.
        due_date: Optional due-date string for invoices.
    """

    name: str | None = None
    description: str | None = None
    grade: str | None = None
    amount: float | None = None
    currency: str | None = None
    academic_year: str | None = None
    term: str | None = None
    due_date: str | None = None


class FeeStructureUpdate(BaseModel):
    """Schema for partially updating an existing fee structure.

    Only fields that are explicitly set (``exclude_unset=True``) will be
    applied to the record.
    """

    name: str | None = None
    description: str | None = None
    grade: str | None = None
    amount: float | None = None
    currency: str | None = None
    academic_year: str | None = None
    term: str | None = None
    due_date: str | None = None


class FeeStructureResponse(BaseModel):
    """Response schema returned when reading a fee structure.

    Populated from the ``FeeStructure`` ORM model via ``from_attributes`` mode.
    """

    id: str
    school_id: str
    name: str
    description: str | None = None
    grade: str | None = None
    amount: float
    currency: str
    academic_year: str | None = None
    term: str | None = None
    due_date: str | None = None
    is_published: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentInvoiceResponse(BaseModel):
    """Response schema for a student invoice.

    Populated from the ``StudentInvoice`` ORM model via ``from_attributes``
    mode. Includes payment tracking fields (amount_paid, balance, status).
    """

    id: str
    school_id: str
    student_id: str
    fee_structure_id: str
    invoice_number: str
    amount: float
    amount_paid: float
    balance: float
    status: str
    due_date: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvoiceGenerationResponse(BaseModel):
    """Response schema returned after bulk invoice generation.

    Attributes:
        count: The number of invoices that were created.
    """

    count: int
