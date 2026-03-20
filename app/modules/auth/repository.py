"""Data-access layer for authentication and user management.

Provides low-level CRUD operations on the ``users`` table via
SQLAlchemy async sessions.  All methods flush but do not commit;
the caller (typically a service or unit-of-work) is responsible for
committing the transaction.
"""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User


class AuthRepository:
    """Repository handling persistence operations for :class:`User` entities.

    Args:
        session: An active SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> User | None:
        """Look up a user by email address.

        Args:
            email: The email to search for.

        Returns:
            The matching ``User`` or ``None`` if not found.
        """
        result = await self.session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> User | None:
        """Look up a user by primary key.

        Args:
            user_id: UUID string of the user.

        Returns:
            The matching ``User`` or ``None`` if not found.
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def increment_token_version(self, user_id: str) -> None:
        """Bump the token version for a user, invalidating all existing JWTs.

        Args:
            user_id: UUID string of the user whose tokens should be revoked.
        """
        await self.session.execute(
            update(User).where(User.id == user_id).values(token_version=User.token_version + 1)
        )

    async def get_users_by_school(self, school_id: str) -> list[User]:
        """Return all users belonging to a school, newest first.

        Args:
            school_id: UUID of the school.

        Returns:
            List of ``User`` instances ordered by ``created_at`` descending.
        """
        result = await self.session.execute(
            select(User).where(User.school_id == school_id).order_by(User.created_at.desc())
        )
        return list(result.scalars().all())

    async def create_user(self, user: User) -> User:
        """Persist a new user to the database.

        Args:
            user: A populated ``User`` instance (not yet added to the session).

        Returns:
            The same ``User`` instance after flushing (with generated defaults).
        """
        self.session.add(user)
        await self.session.flush()
        return user

    async def update_user(self, user_id: str, data: dict) -> User | None:
        """Apply a partial update to an existing user.

        Only keys present in *data* whose values are not ``None`` and that
        correspond to actual ``User`` attributes are written.

        Args:
            user_id: UUID of the user to update.
            data: Mapping of field names to new values.

        Returns:
            The updated ``User``, or ``None`` if the user does not exist.
        """
        result = await self.session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        if not user:
            return None
        for key, value in data.items():
            if hasattr(user, key) and value is not None:
                setattr(user, key, value)
        await self.session.flush()
        return user
