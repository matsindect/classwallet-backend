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
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.fees.schemas import StudentInvoiceResponse
from app.modules.reports.schemas import ReportOverview
from app.modules.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/overview", response_model=ReportOverview)
async def get_overview(
    current_user: UserResponse = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """Get a financial overview report for the current user's school.

    Requires the ``view_reports`` permission. Returns aggregate statistics
    including total students, invoiced/collected/outstanding amounts, and
    the collection rate.

    Args:
        current_user: The authenticated user (injected).
        service: The ReportService instance (injected).
        from_date: Start of the date range (required).
        to_date: End of the date range (required).

    Returns:
        A ReportOverview with aggregate financial statistics.
    """
    enforce(current_user.role, "view_reports")
    return await service.get_overview(current_user.school_id, from_date, to_date)


@router.get("/outstanding", response_model=list[StudentInvoiceResponse])
async def get_outstanding(
    current_user: UserResponse = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
    from_date: datetime = Query(..., alias="from"),
    to_date: datetime = Query(..., alias="to"),
):
    """List all outstanding invoices for the current user's school.

    Requires the ``view_reports`` permission. Returns invoices that
    still have an unpaid balance.

    Args:
        current_user: The authenticated user (injected).
        service: The ReportService instance (injected).
        from_date: Start of the date range (required).
        to_date: End of the date range (required).

    Returns:
        A list of StudentInvoiceResponse objects for outstanding invoices.
    """
    enforce(current_user.role, "view_reports")
    invoices = await service.get_outstanding(current_user.school_id)
    return [StudentInvoiceResponse.model_validate(i) for i in invoices]


@router.get("/export")
async def export_report(
    current_user: UserResponse = Depends(get_current_user),
    service: ReportService = Depends(get_report_service),
    reportType: str = Query(...),  # noqa: N803
):
    """Export school data as a downloadable CSV file.

    Requires the ``view_reports`` permission. Supports report types:
    "students", "invoices", and "outstanding".

    Args:
        current_user: The authenticated user (injected).
        service: The ReportService instance (injected).
        reportType: The type of report to export.

    Returns:
        A StreamingResponse with CSV content and appropriate download headers.
    """
    enforce(current_user.role, "view_reports")
    csv_content = await service.export_csv(current_user.school_id, reportType)

    return StreamingResponse(
        iter([csv_content]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={reportType}_report.csv"},
    )
