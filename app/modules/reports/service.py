"""Service layer for report generation.

Provides business logic for financial overview statistics, outstanding
invoice retrieval, and CSV export of various report types (students,
invoices, outstanding balances).
"""

import csv
import io
from collections import defaultdict
from datetime import datetime

from app.modules.fees.repository import FeeRepository
from app.modules.payments.repository import PaymentRepository
from app.modules.students.repository import StudentRepository


class ReportService:
    """Business logic service for generating school reports.

    Aggregates data from students, fees/invoices, and payments repositories
    to produce overview statistics, outstanding invoice lists, and CSV
    exports.
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

    async def get_overview(self, school_id: str, from_date: datetime, to_date: datetime) -> dict:
        """Generate a financial overview report matching the API contract.

        Returns a dict with keys matching ReportOverview schema fields
        (snake_case), already suitable for CamelModel serialisation.
        """
        students = await self.student_repo.get_all_students(school_id)
        invoices = await self.fee_repo.list_invoices(school_id)
        payments = await self.payment_repo.get_payments_in_range(school_id, from_date, to_date)

        total_invoiced = sum(inv.amount for inv in invoices)
        total_collected = sum(p.amount for p in payments)
        outstanding_balance = sum(inv.balance for inv in invoices)
        collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else 0.0

        # --- Student payment status counts ---
        paid_students = 0
        partial_students = 0
        unpaid_students = 0

        # Build a map of student_id -> list of invoices
        student_invoices: dict[str, list] = defaultdict(list)
        for inv in invoices:
            student_invoices[inv.student_id].append(inv)

        for sid in student_invoices:
            invs = student_invoices[sid]
            total_balance = sum(i.balance for i in invs)
            total_amount = sum(i.amount for i in invs)
            if total_balance <= 0:
                paid_students += 1
            elif total_balance < total_amount:
                partial_students += 1
            else:
                unpaid_students += 1

        # Count students with no invoices as having nothing to pay (not "unpaid")
        # They are already counted in total_students but not in any payment bucket.

        # --- Collection by grade ---
        # TODO: Expand with full grade-level aggregation when invoice→student
        #       join is available in the repository layer.
        grade_collected: dict[str, float] = defaultdict(float)
        grade_outstanding: dict[str, float] = defaultdict(float)

        student_grade_map = {s.id: getattr(s, "grade", "Unknown") for s in students}
        for inv in invoices:
            grade = student_grade_map.get(inv.student_id, "Unknown")
            grade_collected[grade] += inv.amount - inv.balance
            grade_outstanding[grade] += inv.balance

        collection_by_grade = [
            {
                "grade": g,
                "collected": round(grade_collected[g], 2),
                "outstanding": round(grade_outstanding[g], 2),
            }
            for g in sorted(grade_collected.keys())
        ]

        # --- Collection trend (payments grouped by date) ---
        date_totals: dict[str, float] = defaultdict(float)
        for p in payments:
            day = (
                p.created_at.strftime("%Y-%m-%d")
                if hasattr(p, "created_at") and p.created_at
                else "unknown"
            )
            date_totals[day] += p.amount

        collection_trend = [
            {"date": d, "amount": round(date_totals[d], 2)} for d in sorted(date_totals.keys())
        ]

        # --- Top overdue students (top 10 by outstanding balance) ---
        student_balances: dict[str, float] = defaultdict(float)
        for inv in invoices:
            if inv.balance > 0:
                student_balances[inv.student_id] += inv.balance

        student_map = {s.id: s for s in students}
        sorted_overdue = sorted(student_balances.items(), key=lambda x: x[1], reverse=True)[:10]
        top_overdue_students = []
        for sid, balance in sorted_overdue:
            s = student_map.get(sid)
            if s:
                top_overdue_students.append(
                    {
                        "student": {
                            "firstName": s.first_name,
                            "lastName": s.last_name,
                            "studentId": getattr(s, "student_id", sid),
                            "grade": getattr(s, "grade", "Unknown"),
                        },
                        "balance": round(balance, 2),
                    }
                )

        return {
            "totalCollected": round(total_collected, 2),
            "outstandingBalance": round(outstanding_balance, 2),
            "collectionRate": round(collection_rate, 2),
            "totalStudents": len(students),
            "paidStudents": paid_students,
            "partialStudents": partial_students,
            "unpaidStudents": unpaid_students,
            "collectionByGrade": collection_by_grade,
            "collectionTrend": collection_trend,
            "topOverdueStudents": top_overdue_students,
        }

    async def get_outstanding(self, school_id: str) -> list:
        """Retrieve all outstanding (unpaid) invoices for a school."""
        return await self.fee_repo.get_outstanding_invoices(school_id)

    async def export_csv(
        self,
        school_id: str,
        report_type: str,
        from_date: datetime,
        to_date: datetime,
    ) -> str:
        """Export school data as a CSV string.

        Supports report types: "collections", "outstanding", "enrolment".
        """
        output = io.StringIO()
        writer = csv.writer(output)

        if report_type == "collections":
            writer.writerow(
                [
                    "Invoice Number",
                    "Student ID",
                    "Amount",
                    "Amount Paid",
                    "Balance",
                    "Status",
                    "Due Date",
                ]
            )
            invoices = await self.fee_repo.list_invoices(school_id)
            for inv in invoices:
                writer.writerow(
                    [
                        inv.invoice_number,
                        inv.student_id,
                        inv.amount,
                        inv.amount_paid,
                        inv.balance,
                        inv.status,
                        inv.due_date,
                    ]
                )

        elif report_type == "outstanding":
            writer.writerow(
                ["Invoice Number", "Student ID", "Amount", "Amount Paid", "Balance", "Status"]
            )
            invoices = await self.fee_repo.get_outstanding_invoices(school_id)
            for inv in invoices:
                writer.writerow(
                    [
                        inv.invoice_number,
                        inv.student_id,
                        inv.amount,
                        inv.amount_paid,
                        inv.balance,
                        inv.status,
                    ]
                )

        elif report_type == "enrolment":
            writer.writerow(["ID", "First Name", "Last Name", "Grade", "Status", "Email"])
            students = await self.student_repo.get_all_students(school_id)
            for s in students:
                writer.writerow(
                    [s.id, s.first_name, s.last_name, s.grade, s.status, getattr(s, "email", "")]
                )

        else:
            raise ValueError(f"Unsupported report type: {report_type}")

        return output.getvalue()
