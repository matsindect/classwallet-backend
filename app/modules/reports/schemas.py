"""Pydantic schemas for the reports module.

Defines response models for reporting endpoints, including high-level
financial overview statistics for a school.
"""

from pydantic import BaseModel

from app.modules.fees.schemas import StudentInvoiceResponse


class ReportOverview(BaseModel):
    """Response schema for the financial overview report.

    Provides aggregate statistics about students, invoicing, and
    payment collection for a school within a given time period.

    Attributes:
        total_students: Total number of enrolled students.
        total_invoiced: Sum of all invoice amounts.
        total_collected: Sum of all collected payments.
        total_outstanding: Sum of remaining balances across invoices.
        collection_rate: Percentage of invoiced amount that has been collected.
    """
    total_students: int
    total_invoiced: float
    total_collected: float
    total_outstanding: float
    collection_rate: float
