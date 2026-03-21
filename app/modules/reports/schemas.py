"""Pydantic schemas for the reports module.

Defines response models for reporting endpoints, including high-level
financial overview statistics for a school.  All schemas inherit from
CamelModel so field names are serialised as camelCase.
"""

from app.core.schemas import CamelModel


class GradeCollection(CamelModel):
    """Collection totals broken down by grade."""

    grade: str
    collected: float
    outstanding: float


class CollectionTrend(CamelModel):
    """Daily collection amount for trend charting."""

    date: str
    amount: float


class OverdueStudentSummary(CamelModel):
    """Top-overdue student with identifying info and balance."""

    student: dict  # {firstName, lastName, studentId, grade}
    balance: float


class ReportOverview(CamelModel):
    """Response schema for the financial overview report.

    Provides aggregate statistics about students, invoicing, and
    payment collection for a school within a given time period.
    """

    total_collected: float
    outstanding_balance: float
    collection_rate: float
    total_students: int
    paid_students: int
    partial_students: int
    unpaid_students: int
    collection_by_grade: list[GradeCollection]
    collection_trend: list[CollectionTrend]
    top_overdue_students: list[OverdueStudentSummary]
