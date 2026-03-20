"""FastAPI router for payment endpoints.

Exposes paginated payment listing, single payment retrieval, and
daily reconciliation summary endpoints. All endpoints enforce
role-based access control via policy.enforce().
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.di import get_payment_service
from app.core.pagination import clamp_pagination, paginate
from app.core.policy import enforce
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.payments.schemas import PaymentResponse, ReconciliationSummary
from app.modules.payments.service import PaymentService

router = APIRouter(prefix="/payments", tags=["Payments"])


@router.get("")
async def list_payments(
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
    status: str | None = None,
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    studentId: str | None = None,
    page: int | None = Query(None),
    pageSize: int | None = Query(None),
):
    """List payments with optional filters and pagination.

    Requires the ``view_payments`` permission. Supports filtering by status,
    date range, and student ID. Returns a paginated response.

    Args:
        current_user: The authenticated user (injected).
        service: The PaymentService instance (injected).
        status: Optional filter by payment status.
        from_date: Optional start of date range filter.
        to_date: Optional end of date range filter.
        studentId: Optional filter by student ID.
        page: Page number (1-based).
        pageSize: Number of items per page.

    Returns:
        A paginated dict containing payment records and metadata.
    """
    enforce(current_user.role, "view_payments")
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
    data = [PaymentResponse.model_validate(pm) for pm in items]
    return paginate(data, total, p, ps)


@router.get("/reconciliation", response_model=list[ReconciliationSummary])
async def get_reconciliation(
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """Get a daily reconciliation summary for a date range.

    Requires the ``manage_payments`` permission. Returns daily aggregates
    of collected amounts and payment counts, broken down by payment method.

    Args:
        current_user: The authenticated user (injected).
        service: The PaymentService instance (injected).
        from_date: Start of the date range (required).
        to_date: End of the date range (required).

    Returns:
        A list of ReconciliationSummary objects, one per day.
    """
    enforce(current_user.role, "manage_payments")
    return await service.get_reconciliation(
        school_id=current_user.school_id,
        from_date=from_date,
        to_date=to_date,
    )


@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: str,
    current_user: UserResponse = Depends(get_current_user),
    service: PaymentService = Depends(get_payment_service),
):
    """Retrieve a single payment by its ID.

    Requires the ``view_payments`` permission.

    Args:
        payment_id: The UUID of the payment to retrieve.
        current_user: The authenticated user (injected).
        service: The PaymentService instance (injected).

    Returns:
        A PaymentResponse with the payment details.

    Raises:
        NotFoundError: If no payment with the given ID exists.
    """
    enforce(current_user.role, "view_payments")
    payment = await service.get_payment(payment_id)
    return PaymentResponse.model_validate(payment)
