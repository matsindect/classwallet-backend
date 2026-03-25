"""ZB Bank integration API router.

Exposes endpoints for viewing bank transactions, unmatched payments,
and reconciliation run history.
"""

from fastapi import APIRouter, Depends, Query

from app.core.database import async_session_factory
from app.core.pagination import clamp_pagination
from app.core.response import paginated_response, success_response
from app.modules.auth.dependencies import require_school_user
from app.modules.auth.schemas import UserResponse
from app.modules.zb_bank.repository import ZBBankRepository
from app.modules.zb_bank.schemas import (
    ZBReconciliationRunResponse,
    ZBTransactionResponse,
    ZBUnmatchedSummary,
)

router = APIRouter(prefix="/zb-bank", tags=["ZB Bank"])


@router.get("/transactions")
async def list_transactions(
    current_user: UserResponse = Depends(require_school_user),
    is_matched: bool | None = Query(None),
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List ZB Bank transactions with optional match status filter."""
    p, ps = clamp_pagination(page, pageSize)
    offset = (p - 1) * ps

    async with async_session_factory() as session:
        repo = ZBBankRepository(session)
        txns, total = await repo.list_transactions(
            school_id=current_user.school_id,
            offset=offset,
            limit=ps,
            is_matched=is_matched,
        )

    data = [ZBTransactionResponse.model_validate(t).model_dump(by_alias=True) for t in txns]
    return paginated_response(data=data, page=p, page_size=ps, total_count=total)


@router.get("/transactions/unmatched/summary")
async def unmatched_summary(
    current_user: UserResponse = Depends(require_school_user),
):
    """Get a summary of all unmatched bank transactions."""
    async with async_session_factory() as session:
        repo = ZBBankRepository(session)
        unmatched = await repo.get_unmatched_transactions(current_user.school_id)

    total_amount = sum(t.amount for t in unmatched)
    dates = [t.date or t.transaction_date for t in unmatched if t.date or t.transaction_date]

    summary = ZBUnmatchedSummary(
        total_unmatched=len(unmatched),
        total_amount=round(total_amount, 2),
        oldest_transaction_date=min(dates) if dates else None,
        newest_transaction_date=max(dates) if dates else None,
    )
    return success_response(data=summary.model_dump(by_alias=True))


@router.get("/reconciliation-runs")
async def list_reconciliation_runs(
    current_user: UserResponse = Depends(require_school_user),
    limit: int = Query(20, le=100),
):
    """List recent reconciliation runs."""
    async with async_session_factory() as session:
        repo = ZBBankRepository(session)
        runs = await repo.list_reconciliation_runs(school_id=current_user.school_id, limit=limit)

    data = [ZBReconciliationRunResponse.model_validate(r).model_dump(by_alias=True) for r in runs]
    return success_response(data=data)
