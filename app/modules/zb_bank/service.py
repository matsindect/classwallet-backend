"""Internal background service for ZB Bank integration.

Polls bank transactions from the ZB Bank API, stores them locally,
matches them against outstanding invoices, creates payment records,
and updates invoice balances. Designed to run as a background task
(not exposed via REST endpoints). Manages its own database sessions.
"""

import re
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.modules.audit.repository import AuditRepository
from app.modules.fees.models import StudentInvoice
from app.modules.fees.repository import FeeRepository
from app.modules.payments.models import Payment
from app.modules.payments.repository import PaymentRepository
from app.modules.students.repository import StudentRepository
from app.modules.zb_bank.client import ZBBankClient
from app.modules.zb_bank.models import ZBReconciliationRun, ZBTransaction
from app.modules.zb_bank.repository import ZBBankRepository

logger = get_logger(__name__)

# Actor ID used for audit logs from background tasks
SYSTEM_ACTOR = "system:zb-bank-poller"


class ZBBankService:
    """Internal service for polling ZB Bank and reconciling transactions.

    Manages its own database session (not injected via FastAPI DI) so it
    can run as a standalone background task outside of HTTP request scope.

    Args:
        session: An async SQLAlchemy session for database operations.
        client: HTTP client for calling ZB Bank APIs.
    """

    def __init__(self, session: AsyncSession, client: ZBBankClient | None = None):
        self.session = session
        self.client = client or ZBBankClient()
        self.zb_repo = ZBBankRepository(session)
        self.fee_repo = FeeRepository(session)
        self.payment_repo = PaymentRepository(session)
        self.student_repo = StudentRepository(session)
        self.audit_repo = AuditRepository(session)

    async def poll_and_reconcile(self, school_id: str) -> dict:
        """Poll pending payments from ZB Bank and reconcile in one step.

        This is the primary method called by the background scheduler.
        It fetches pending transactions, stores new ones, then runs
        reconciliation to match them against outstanding invoices.

        Args:
            school_id: The school to poll and reconcile for.

        Returns:
            A dict with poll and reconciliation results.
        """
        poll_result = await self.poll_pending_payments(school_id)
        reconcile_result = await self.reconcile(school_id)

        logger.info(
            "zb_bank_poll_and_reconcile_complete",
            school_id=school_id,
            new_transactions=poll_result["new_stored"],
            matched=reconcile_result["matched_count"],
            unmatched=reconcile_result["unmatched_count"],
        )

        return {
            "poll": poll_result,
            "reconciliation": reconcile_result,
        }

    async def poll_all_payments(self, school_id: str) -> dict:
        """Poll all payment transactions from ZB Bank and store new ones.

        Fetches the full transaction list from ZB Bank, deduplicates against
        already-stored records (by ``zb_id``), and persists new transactions.

        Args:
            school_id: The school to associate transactions with.

        Returns:
            A dict with total_fetched, new_stored, and duplicates_skipped counts.
        """
        raw_transactions = await self.client.fetch_all_payments()
        return await self._store_transactions(raw_transactions, school_id, "poll_all")

    async def poll_pending_payments(self, school_id: str) -> dict:
        """Poll only pending payment transactions from ZB Bank.

        Fetches pending (unpicked) transactions and stores new ones locally.

        Args:
            school_id: The school to associate transactions with.

        Returns:
            A dict with total_fetched, new_stored, and duplicates_skipped counts.
        """
        raw_transactions = await self.client.fetch_pending_payments()
        return await self._store_transactions(raw_transactions, school_id, "poll_pending")

    async def _store_transactions(
        self, raw_transactions: list[dict], school_id: str, action: str
    ) -> dict:
        """Store raw ZB Bank transactions, skipping duplicates.

        Args:
            raw_transactions: List of transaction dicts from ZB Bank API.
            school_id: The school to associate with.
            action: Audit action name.

        Returns:
            A dict with total_fetched, new_stored, and duplicates_skipped.
        """
        new_stored = 0
        duplicates_skipped = 0

        for raw in raw_transactions:
            zb_id = str(raw.get("id", ""))
            if not zb_id:
                continue

            existing = await self.zb_repo.get_transaction_by_zb_id(school_id, zb_id)
            if existing:
                duplicates_skipped += 1
                continue

            txn = ZBTransaction(
                school_id=school_id,
                zb_id=zb_id,
                amount=float(raw.get("amount", 0)),
                date=raw.get("date"),
                transaction_date=raw.get("transactionDate"),
                narrative=raw.get("narrative"),
                reference=raw.get("reference"),
                source=raw.get("source"),
                status=raw.get("status"),
                nr1=raw.get("nr1"),
                nr2=raw.get("nr2"),
                nr3=raw.get("nr3"),
                nr4=raw.get("nr4"),
                picked=raw.get("picked"),
                tcd=raw.get("tcd"),
            )
            await self.zb_repo.create_transaction(txn)
            new_stored += 1

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=SYSTEM_ACTOR,
            action=f"zb_bank_{action}",
            entity="zb_transaction",
            metadata={
                "total_fetched": len(raw_transactions),
                "new_stored": new_stored,
                "duplicates_skipped": duplicates_skipped,
            },
        )

        logger.info(
            "zb_bank_poll_complete",
            action=action,
            total_fetched=len(raw_transactions),
            new_stored=new_stored,
            duplicates_skipped=duplicates_skipped,
        )

        return {
            "total_fetched": len(raw_transactions),
            "new_stored": new_stored,
            "duplicates_skipped": duplicates_skipped,
        }

    async def reconcile(self, school_id: str) -> dict:
        """Match unmatched ZB Bank transactions to outstanding invoices.

        For each unmatched transaction, attempts to find a matching invoice
        by searching for an invoice number pattern (``INV-XXXXXXXX``) in the
        transaction's reference, narrative, nr1, nr2, nr3, and nr4 fields.

        When matched, creates a Payment record, updates the invoice balance,
        and marks the transaction as matched.

        Args:
            school_id: The school to reconcile for.

        Returns:
            A dict with run_id, total_transactions, matched_count,
            unmatched_count, total_amount_reconciled, and status.
        """
        run = ZBReconciliationRun(school_id=school_id, status="in_progress")
        await self.zb_repo.create_reconciliation_run(run)

        unmatched_txns = await self.zb_repo.get_unmatched_transactions(school_id)
        outstanding_invoices = await self.fee_repo.get_outstanding_invoices(school_id)

        # Build a lookup of invoice_number -> invoice for fast matching
        invoice_lookup: dict[str, StudentInvoice] = {
            inv.invoice_number.upper(): inv for inv in outstanding_invoices
        }

        matched_count = 0
        unmatched_count = 0
        total_reconciled = 0.0

        for txn in unmatched_txns:
            invoice = self._find_matching_invoice(txn, invoice_lookup)

            if invoice:
                # Create a payment record
                payment_amount = min(txn.amount, invoice.balance)
                payment = Payment(
                    school_id=school_id,
                    student_id=invoice.student_id,
                    invoice_id=invoice.id,
                    amount=payment_amount,
                    method="bank_transfer",
                    reference=txn.reference or txn.zb_id,
                    status="completed",
                    notes=f"Auto-reconciled from ZB Bank transaction {txn.zb_id}",
                    paid_at=datetime.now(UTC),
                    created_by=SYSTEM_ACTOR,
                )
                await self.payment_repo.create_payment(payment)

                # Update invoice balance
                invoice.amount_paid = round(invoice.amount_paid + payment_amount, 2)
                invoice.balance = round(invoice.amount - invoice.amount_paid, 2)
                if invoice.balance <= 0:
                    invoice.balance = 0.0
                    invoice.status = "paid"
                else:
                    invoice.status = "partial"
                await self.session.flush()

                # Mark transaction as matched
                await self.zb_repo.update_transaction_match(txn.id, invoice.id, payment.id)

                matched_count += 1
                total_reconciled += payment_amount

                logger.info(
                    "zb_bank_transaction_matched",
                    zb_id=txn.zb_id,
                    invoice=invoice.invoice_number,
                    amount=payment_amount,
                )
            else:
                unmatched_count += 1

        # Update run record
        run.completed_at = datetime.now(UTC)
        run.total_transactions = len(unmatched_txns)
        run.matched_count = matched_count
        run.unmatched_count = unmatched_count
        run.total_amount_reconciled = round(total_reconciled, 2)
        run.status = "completed"
        await self.session.flush()

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=SYSTEM_ACTOR,
            action="zb_bank_reconcile",
            entity="zb_reconciliation_run",
            entity_id=run.id,
            metadata={
                "total_transactions": len(unmatched_txns),
                "matched": matched_count,
                "unmatched": unmatched_count,
                "amount_reconciled": round(total_reconciled, 2),
            },
        )

        return {
            "run_id": run.id,
            "total_transactions": len(unmatched_txns),
            "matched_count": matched_count,
            "unmatched_count": unmatched_count,
            "total_amount_reconciled": round(total_reconciled, 2),
            "status": "completed",
        }

    def _find_matching_invoice(
        self, txn: ZBTransaction, invoice_lookup: dict[str, StudentInvoice]
    ) -> StudentInvoice | None:
        """Attempt to match a bank transaction to an invoice.

        Searches the transaction's reference, narrative, and nr1-nr4 fields
        for a pattern matching ``INV-XXXXXXXX`` (the invoice number format).
        Falls back to exact lookup of the full reference field.

        Args:
            txn: The ZB Bank transaction to match.
            invoice_lookup: Dict mapping uppercase invoice numbers to invoices.

        Returns:
            The matched StudentInvoice, or None if no match found.
        """
        search_fields = [
            txn.reference,
            txn.narrative,
            txn.nr1,
            txn.nr2,
            txn.nr3,
            txn.nr4,
        ]

        invoice_pattern = re.compile(r"(INV-[A-Z0-9]+)", re.IGNORECASE)

        for field in search_fields:
            if not field:
                continue
            matches = invoice_pattern.findall(field)
            for match in matches:
                invoice = invoice_lookup.get(match.upper())
                if invoice and invoice.balance > 0:
                    return invoice

        # Fallback: try the raw reference as an exact invoice number
        if txn.reference:
            invoice = invoice_lookup.get(txn.reference.strip().upper())
            if invoice and invoice.balance > 0:
                return invoice

        return None

    async def upload_student(self, school_id: str, student_id: str) -> dict:
        """Upload a student's details to ZB Bank for bill-pay registration.

        Looks up the student by ID, then calls the ZB Bank student-details
        endpoint to register them.

        Args:
            school_id: The school the student belongs to.
            student_id: The internal student UUID.

        Returns:
            A dict with success, message, and student_id.

        Raises:
            NotFoundError: If the student does not exist.
        """
        from app.core.errors import NotFoundError

        student = await self.student_repo.get_by_id(student_id)
        if not student or student.school_id != school_id:
            raise NotFoundError(message="Student not found")

        customer_name = f"{student.first_name} {student.last_name}"
        await self.client.upload_student_details(
            customer_account=student.id,
            customer_name=customer_name,
            level=student.grade or "",
        )

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=SYSTEM_ACTOR,
            action="zb_bank_student_upload",
            entity="student",
            entity_id=student_id,
            metadata={"customer_name": customer_name},
        )

        logger.info(
            "zb_bank_student_uploaded",
            student_id=student_id,
            customer_name=customer_name,
        )

        return {
            "success": True,
            "message": "Student details uploaded to ZB Bank",
            "student_id": student_id,
        }
