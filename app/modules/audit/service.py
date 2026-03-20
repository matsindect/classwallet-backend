"""Service layer for audit log business logic.

Provides paginated, filtered access to the audit trail for a school.
"""

from datetime import datetime

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository


class AuditService:
    """Business logic service for querying audit logs.

    Provides paginated listing of audit log entries with optional
    filters for date range, actor, and action type.

    Args:
        repo: Repository for audit log data access.
    """

    def __init__(self, repo: AuditRepository):
        self.repo = repo

    async def list_logs(
        self,
        school_id: str,
        page: int,
        page_size: int,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        actor: str | None = None,
        action: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        """List audit logs with pagination and optional filters.

        Converts 1-based page numbers to database offsets and delegates
        to the repository.

        Args:
            school_id: The school to scope logs to.
            page: The 1-based page number.
            page_size: Number of records per page.
            from_date: Optional lower bound (inclusive) on timestamp.
            to_date: Optional upper bound (inclusive) on timestamp.
            actor: Optional filter by actor ID.
            action: Optional filter by action type.

        Returns:
            A tuple of (list of AuditLog objects, total matching count).
        """
        offset = (page - 1) * page_size
        return await self.repo.list_logs(
            school_id=school_id,
            offset=offset,
            limit=page_size,
            from_date=from_date,
            to_date=to_date,
            actor=actor,
            action=action,
        )
