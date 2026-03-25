"""FastAPI router for report endpoints.

Exposes endpoints for financial overview statistics, outstanding invoice
listing, and CSV data export. All endpoints enforce role-based access
control via policy.enforce().
"""

from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from app.core.di import get_report_service
from app.core.policy import enforce
from app.core.response import error_response, success_response
from app.modules.auth.dependencies import require_school_user
from app.modules.auth.schemas import UserResponse
from app.modules.fees.schemas import StudentInvoiceResponse
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/overview")
async def get_overview(
    current_user: UserResponse = Depends(require_school_user),
    service: ReportService = Depends(get_report_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """Get a financial overview report for the current user's school.

    Requires the ``reports.read`` permission. Returns aggregate statistics
    including total students, invoiced/collected/outstanding amounts, and
    the collection rate.
    """
    enforce(current_user, "reports.read")
    overview = await service.get_overview(current_user.school_id, from_date, to_date)
    return success_response(data=overview)


@router.get("/outstanding")
async def get_outstanding(
    current_user: UserResponse = Depends(require_school_user),
    service: ReportService = Depends(get_report_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """List all outstanding invoices for the current user's school.

    Requires the ``reports.read`` permission. Returns invoices that
    still have an unpaid balance.
    """
    enforce(current_user, "reports.read")
    invoices = await service.get_outstanding(current_user.school_id)
    data = [StudentInvoiceResponse.model_validate(i).model_dump(by_alias=True) for i in invoices]
    return success_response(data=data)


@router.get("/export")
async def export_report(
    current_user: UserResponse = Depends(require_school_user),
    service: ReportService = Depends(get_report_service),
    reportType: str = Query(...),  # noqa: N803
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """Export school data as a downloadable CSV file.

    Requires the ``reports.export`` permission. Supports report types:
    "collections", "outstanding", and "enrolment".

    On success returns a raw CSV stream. On error falls back to
    the standard JSON error envelope.
    """
    enforce(current_user, "reports.export")
    try:
        csv_content = await service.export_csv(
            current_user.school_id,
            reportType,
            from_date,
            to_date,
        )
    except ValueError as exc:
        return error_response(code="VALIDATION_ERROR", message=str(exc))

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={reportType}_report.csv"},
    )
