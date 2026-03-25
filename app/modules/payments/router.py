"""FastAPI router for payment endpoints.

Exposes paginated payment listing, single payment retrieval, and
daily reconciliation summary endpoints. All endpoints enforce
role-based access control via policy.enforce().
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.di import get_payment_service
from app.core.pagination import clamp_pagination
from app.core.policy import enforce
from app.core.response import paginated_response, success_response
from app.modules.auth.dependencies import require_school_user
from app.modules.auth.schemas import UserResponse
from app.modules.payments.schemas import PaymentResponse, ReconciliationSummary
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("")
async def list_payments(
    current_user: UserResponse = Depends(require_school_user),
    service: PaymentService = Depends(get_payment_service),
    status: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    studentId: str | None = None,  # noqa: N803
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List payments with optional filters and pagination.

    Requires the ``payments.read`` permission. Supports filtering by status,
    date range, and student ID. Returns a paginated response.
    """
    enforce(current_user, "payments.read")
    p, ps = clamp_pagination(page, pageSize)
    items, total = await service.list_payments(
        school_id=current_user.school_id,
        page=p,
        page_size=ps,
        status=status,
        from_date=from_date,
        to_date=to_date,
        student_id=studentId,
    )
    data = [PaymentResponse.from_model(pm).model_dump(by_alias=True) for pm in items]
    return paginated_response(data=data, page=p, page_size=ps, total_count=total)


@router.get("/reconciliation")
async def get_reconciliation(
    current_user: UserResponse = Depends(require_school_user),
    service: PaymentService = Depends(get_payment_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """Get a daily reconciliation summary for a date range.

    Requires the ``payments.reconcile`` permission. Returns daily aggregates
    of collected amounts and payment counts.
    """
    enforce(current_user, "payments.reconcile")
    summaries = await service.get_reconciliation(
        school_id=current_user.school_id,
        from_date=from_date,
        to_date=to_date,
    )
    data = [ReconciliationSummary(**s).model_dump(by_alias=True) for s in summaries]
    return success_response(data=data)


@router.get("/{payment_id}")
async def get_payment(
    payment_id: str,
    current_user: UserResponse = Depends(require_school_user),
    service: PaymentService = Depends(get_payment_service),
):
    """Retrieve a single payment by its ID.

    Requires the ``payments.read`` permission.
    """
    enforce(current_user, "payments.read")
    payment = await service.get_payment(payment_id)
    data = PaymentResponse.from_model(payment).model_dump(by_alias=True)
    return success_response(data=data)
