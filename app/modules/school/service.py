"""Business-logic layer for school profile management.

Handles retrieval and updates of school records, with audit logging for
all mutations.
"""

from app.core.errors import NotFoundError
from app.modules.audit.repository import AuditRepository
from app.modules.school.models import School
from app.modules.school.repository import SchoolRepository


class SchoolService:
    """Service encapsulating school profile operations.

    Args:
        repo: Repository for school persistence operations.
        audit_repo: Repository for writing audit-log entries.
    """

    def __init__(self, repo: SchoolRepository, audit_repo: AuditRepository):
        self.repo = repo
        self.audit_repo = audit_repo

    async def get_school(self, school_id: str) -> School:
        """Retrieve a school by ID.

        Args:
            school_id: UUID of the school.

        Returns:
            The ``School`` instance.

        Raises:
            NotFoundError: If no school with the given ID exists.
        """
        school = await self.repo.get_school(school_id)
        if not school:
            raise NotFoundError(message="School not found")
        return school

    async def update_school(self, school_id: str, data: dict, actor_id: str) -> School:
        """Update a school's profile and record an audit entry.

        Args:
            school_id: UUID of the school to update.
            data: Mapping of field names to new values.
            actor_id: UUID of the user performing the update (for audit).

        Returns:
            The updated ``School`` instance.

        Raises:
            NotFoundError: If no school with the given ID exists.
        """
        school = await self.repo.update_school(school_id, data)
        if not school:
            raise NotFoundError(message="School not found")
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="school",
            entity_id=school_id,
        )
        return school
