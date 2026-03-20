"""FastAPI router for audit log endpoints.

Exposes a paginated audit log viewer with optional filters for date range,
actor, and action type. Enforces role-based access control via
policy.enforce().
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.di import get_audit_service
from app.core.pagination import clamp_pagination, paginate
from app.core.policy import enforce
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs")
async def list_logs(
    current_user: UserResponse = Depends(get_current_user),
    service: AuditService = Depends(get_audit_service),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    actor: str | None = None,
    action: str | None = None,
    page: int | None = Query(None),
    pageSize: int | None = Query(None),
):
    """List audit logs with optional filters and pagination.

    Requires the ``view_audit`` permission. Supports filtering by date
    range, actor ID, and action type. Returns a paginated response.

    Args:
        current_user: The authenticated user (injected).
        service: The AuditService instance (injected).
        from_date: Optional start of date range filter.
        to_date: Optional end of date range filter.
        actor: Optional filter by actor (user) ID.
        action: Optional filter by action type.
        page: Page number (1-based).
        pageSize: Number of items per page.

    Returns:
        A paginated dict containing audit log entries and metadata.
    """
    enforce(current_user.role, "view_audit")
    p, ps = clamp_pagination(page, pageSize)
    items, total = await service.list_logs(
        school_id=current_user.school_id,
        page=p,
        page_size=ps,
        from_date=from_date,
        to_date=to_date,
        actor=actor,
        action=action,
    )
    data = [AuditLogResponse.model_validate(i) for i in items]
    return paginate(data, total, p, ps)
