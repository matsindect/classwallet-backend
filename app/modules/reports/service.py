"""Service layer for report generation.

Provides business logic for financial overview statistics, outstanding
invoice retrieval, and CSV export of various report types (students,
invoices, outstanding balances).
"""

import csv
import io
from datetime import datetime

from app.modules.fees.repository import FeeRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.students.repository import StudentRepository


class ReportService:
    """Business logic service for generating school reports.

    Aggregates data from students, fees/invoices, and payments repositories
    to produce overview statistics, outstanding invoice lists, and CSV
    exports.

    Args:
        fee_repo: Repository for fee and invoice data access.
        payment_repo: Repository for payment data access.
        student_repo: Repository for student data access.
    """

    def __init__(
        self,
        fee_repo: FeeRepository,
        payment_repo: PaymentRepository,
        student_repo: StudentRepository,
    ):
        self.fee_repo = fee_repo
        self.payment_repo = payment_repo
        self.student_repo = student_repo

    async def get_overview(
        self, school_id: str, from_date: datetime, to_date: datetime
    ) -> dict:
        """Generate a financial overview report for a school.

        Computes aggregate statistics including total students, invoiced
        amounts, collected payments, outstanding balances, and the
        collection rate as a percentage.

        Args:
            school_id: The school to generate the report for.
            from_date: Start of the date range for payment collection data.
            to_date: End of the date range for payment collection data.

        Returns:
            A dict with keys: total_students, total_invoiced, total_collected,
            total_outstanding, and collection_rate.
        """
        students = await self.student_repo.get_all_students(school_id)
        invoices = await self.fee_repo.list_invoices(school_id)
        payments = await self.payment_repo.get_payments_in_range(school_id, from_date, to_date)

        total_invoiced = sum(inv.amount for inv in invoices)
        total_collected = sum(p.amount for p in payments)
        total_outstanding = sum(inv.balance for inv in invoices)
        collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0.0

        return {
            "total_students": len(students),
            "total_invoiced": round(total_invoiced, 2),
            "total_collected": round(total_collected, 2),
            "total_outstanding": round(total_outstanding, 2),
            "collection_rate": round(collection_rate, 2),
        }

    async def get_outstanding(self, school_id: str) -> list:
        """Retrieve all outstanding (unpaid) invoices for a school.

        Args:
            school_id: The school to retrieve outstanding invoices for.

        Returns:
            A list of invoice objects with remaining balances.
        """
        return await self.fee_repo.get_outstanding_invoices(school_id)

    async def export_csv(self, school_id: str, report_type: str) -> str:
        """Export school data as a CSV string.

        Supports three report types:
        - ``students``: Student roster with ID, name, grade, status, email.
        - ``invoices``: All invoices with amounts, balances, and due dates.
        - ``outstanding``: Only invoices with remaining balances.

        Args:
            school_id: The school to export data for.
            report_type: One of "students", "invoices", or "outstanding".

        Returns:
            A CSV-formatted string ready for download.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "students":
            writer.writerow(["ID", "First Name", "Last Name", "Grade", "Status", "Email"])
            students = await self.student_repo.get_all_students(school_id)
            for s in students:
                writer.writerow([s.id, s.first_name, s.last_name, s.grade, s.status, s.email])

        elif report_type == "invoices":
            writer.writerow([
                "Invoice Number", "Student ID", "Amount", "Amount Paid", "Balance", "Status", "Due Date"
            ])
            invoices = await self.fee_repo.list_invoices(school_id)
            for inv in invoices:
                writer.writerow([
                    inv.invoice_number, inv.student_id, inv.amount,
                    inv.amount_paid, inv.balance, inv.status, inv.due_date,
                ])

        elif report_type == "outstanding":
            writer.writerow([
                "Invoice Number", "Student ID", "Amount", "Amount Paid", "Balance", "Status"
            ])
            invoices = await self.fee_repo.get_outstanding_invoices(school_id)
            for inv in invoices:
                writer.writerow([
                    inv.invoice_number, inv.student_id, inv.amount,
                    inv.amount_paid, inv.balance, inv.status,
                ])

        else:
            writer.writerow(["No data for report type: " + report_type])

        return output.getvalue()
