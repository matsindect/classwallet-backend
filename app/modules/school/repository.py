"""Data-access layer for school entities.

Provides low-level CRUD operations on the ``schools`` table via
SQLAlchemy async sessions.  Methods flush but do not commit; the caller
is responsible for committing the transaction.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.school.models import School


class SchoolRepository:
    """Repository handling persistence operations for :class:`School` entities.

    Args:
        session: An active SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_school(self, school_id: str) -> School | None:
        """Retrieve a school by its primary key.

        Args:
            school_id: UUID string of the school.

        Returns:
            The matching ``School`` or ``None`` if not found.
        """
        result = await self.session.execute(select(School).where(School.id == school_id))
        return result.scalar_one_or_none()

    async def list_schools(
        self,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
    ) -> tuple[list[School], int]:
        """Return a paginated list of all schools.

        Args:
            offset: Number of records to skip.
            limit: Maximum number of records to return.
            search: Optional search string (matches name, email, city).

        Returns:
            A tuple of (list of School objects, total count).
        """
        q = select(School)
        count_q = select(func.count(School.id))

        if search:
            pattern = f"%{search}%"
            filter_expr = (
                School.name.ilike(pattern)
                | School.email.ilike(pattern)
                | School.city.ilike(pattern)
            )
            q = q.where(filter_expr)
            count_q = count_q.where(filter_expr)

        total = (await self.session.execute(count_q)).scalar() or 0
        result = await self.session.execute(
            q.order_by(School.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create_school(self, school: School) -> School:
        """Persist a new school record.

        Args:
            school: The School instance to insert.

        Returns:
            The persisted School.
        """
        self.session.add(school)
        await self.session.flush()
        return school

    async def update_school(self, school_id: str, data: dict) -> School | None:
        """Apply a partial update to an existing school.

        Only keys present in *data* whose values are not ``None`` and that
        correspond to actual ``School`` attributes are written.

        Args:
            school_id: UUID of the school to update.
            data: Mapping of field names to new values.

        Returns:
            The updated ``School``, or ``None`` if the school does not exist.
        """
        result = await self.session.execute(select(School).where(School.id == school_id))
        school = result.scalar_one_or_none()
        if not school:
            return None
        for key, value in data.items():
            if hasattr(school, key) and value is not None:
                setattr(school, key, value)
        await self.session.flush()
        return school
