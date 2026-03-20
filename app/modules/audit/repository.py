"""Repository layer for audit log data access.

Provides async database operations for creating audit log entries
and querying them with filters. Used as a cross-cutting concern
by other services to record actions for accountability.
"""

import json
from datetime import datetime

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog


class AuditRepository:
    """Data access object for AuditLog entities.

    Provides methods to create new audit entries and query existing ones
    with pagination and filtering. Intended to be injected into services
    across the application as a cross-cutting concern.

    Args:
        session: An async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def log(
        self,
        school_id: str,
        actor_id: str,
        action: str,
        entity: str,
        entity_id: str | None = None,
        metadata: dict | None = None,
    ) -> AuditLog:
        """Create and persist a new audit log entry.

        Args:
            school_id: The school this action pertains to.
            actor_id: The user or system identifier performing the action.
            action: The action being logged (e.g., "create", "update").
            entity: The type of entity affected (e.g., "payment").
            entity_id: Optional identifier of the specific entity.
            metadata: Optional dict of extra context, serialized as JSON.

        Returns:
            The persisted AuditLog entry.
        """
        entry = AuditLog(
            school_id=school_id,
            actor_id=actor_id,
            action=action,
            entity=entity,
            entity_id=entity_id,
            metadata_json=json.dumps(metadata) if metadata else None,
        )
        self.session.add(entry)
        await self.session.flush()
        return entry

    async def list_logs(
        self,
        school_id: str,
        offset: int = 0,
        limit: int = 20,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
        actor: str | None = None,
        action: str | None = None,
    ) -> tuple[list[AuditLog], int]:
        """Retrieve a paginated list of audit logs with optional filters.

        Args:
            school_id: The school to scope logs to.
            offset: Number of records to skip for pagination.
            limit: Maximum number of records to return.
            from_date: Optional lower bound (inclusive) on timestamp.
            to_date: Optional upper bound (inclusive) on timestamp.
            actor: Optional filter by actor ID.
            action: Optional filter by action type.

        Returns:
            A tuple of (list of AuditLog objects, total matching count).
        """
        q = select(AuditLog).where(AuditLog.school_id == school_id)
        count_q = select(func.count(AuditLog.id)).where(AuditLog.school_id == school_id)

        if from_date:
            q = q.where(AuditLog.timestamp >= from_date)
            count_q = count_q.where(AuditLog.timestamp >= from_date)
        if to_date:
            q = q.where(AuditLog.timestamp <= to_date)
            count_q = count_q.where(AuditLog.timestamp <= to_date)
        if actor:
            q = q.where(AuditLog.actor_id == actor)
            count_q = count_q.where(AuditLog.actor_id == actor)
        if action:
            q = q.where(AuditLog.action == action)
            count_q = count_q.where(AuditLog.action == action)

        total = (await self.session.execute(count_q)).scalar() or 0
        result = await self.session.execute(
            q.order_by(AuditLog.timestamp.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total
