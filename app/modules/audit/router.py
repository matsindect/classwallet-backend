"""FastAPI router for audit log endpoints.

Exposes a paginated audit log viewer with optional filters for date range,
actor, and action type. Enforces role-based access control via
policy.enforce().
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.core.di import get_audit_service
from app.core.pagination import clamp_pagination
from app.core.policy import enforce
from app.core.response import paginated_response
from app.modules.audit.schemas import AuditLogResponse
from app.modules.audit.service import AuditService
from app.modules.auth.dependencies import require_school_user
from app.modules.auth.schemas import UserResponse

router = APIRouter(prefix="/audit", tags=["Audit"])


@router.get("/logs")
async def list_logs(
    current_user: UserResponse = Depends(require_school_user),
    service: AuditService = Depends(get_audit_service),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    actor: str | None = None,
    action: str | None = None,
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List audit logs with optional filters and pagination.

    Requires the ``audit.read`` permission. Supports filtering by date
    range, actor ID, and action type. Returns a paginated response
    wrapped in the standard API envelope.
    """
    enforce(current_user, "audit.read")
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
    data = [AuditLogResponse.from_model(i).model_dump(by_alias=True) for i in items]
    return paginated_response(data=data, page=p, page_size=ps, total_count=total)
