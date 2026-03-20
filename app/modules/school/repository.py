"""Data-access layer for school entities.

Provides low-level CRUD operations on the ``schools`` table via
SQLAlchemy async sessions.  Methods flush but do not commit; the caller
is responsible for committing the transaction.
"""

from sqlalchemy import select
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
