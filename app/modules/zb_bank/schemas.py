"""Pydantic schemas for the ZB Bank integration module."""

from datetime import datetime

from app.core.schemas import CamelModel


class ZBTransactionResponse(CamelModel):
    """A bank transaction fetched from ZB Bank."""

    id: str
    zb_id: str
    amount: float
    date: str | None = None
    transaction_date: str | None = None
    narrative: str | None = None
    reference: str | None = None
    source: str | None = None
    status: str | None = None
    nr1: str | None = None
    nr2: str | None = None
    nr3: str | None = None
    nr4: str | None = None
    is_matched: bool
    matched_invoice_id: str | None = None
    matched_payment_id: str | None = None
    fetched_at: datetime


class ZBReconciliationRunResponse(CamelModel):
    """A reconciliation run record."""

    id: str
    started_at: datetime
    completed_at: datetime | None = None
    total_transactions: int
    matched_count: int
    unmatched_count: int
    skipped_count: int
    total_amount_reconciled: float
    status: str
    error_details: str | None = None


class ZBUnmatchedSummary(CamelModel):
    """Summary of unmatched transactions."""

    total_unmatched: int
    total_amount: float
    oldest_transaction_date: str | None = None
    newest_transaction_date: str | None = None
