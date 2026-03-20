"""Repository layer for reminder data access.

Provides async database operations for reminder configurations
and reminder history records using SQLAlchemy.
"""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.reminders.models import ReminderConfig, ReminderHistory


class ReminderRepository:
    """Data access object for reminder configurations and history.

    Encapsulates all direct database interactions for listing, creating,
    and updating reminder configs, as well as listing reminder history.

    Args:
        session: An async SQLAlchemy session for database operations.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_configs(self, school_id: str) -> list[ReminderConfig]:
        """Retrieve all reminder configurations for a school.

        Args:
            school_id: The school to scope configs to.

        Returns:
            A list of ReminderConfig objects ordered by creation date descending.
        """
        result = await self.session.execute(
            select(ReminderConfig)
            .where(ReminderConfig.school_id == school_id)
            .order_by(ReminderConfig.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_config(self, config_id: str) -> ReminderConfig | None:
        """Fetch a single reminder configuration by ID.

        Args:
            config_id: The UUID of the config to retrieve.

        Returns:
            The ReminderConfig if found, or None.
        """
        result = await self.session.execute(
            select(ReminderConfig).where(ReminderConfig.id == config_id)
        )
        return result.scalar_one_or_none()

    async def create_config(self, config: ReminderConfig) -> ReminderConfig:
        """Persist a new reminder configuration to the database.

        Args:
            config: The ReminderConfig model instance to insert.

        Returns:
            The persisted ReminderConfig object.
        """
        self.session.add(config)
        await self.session.flush()
        return config

    async def update_config(self, config_id: str, data: dict) -> ReminderConfig | None:
        """Update an existing reminder configuration with partial data.

        Only non-None values in the data dict are applied. Fields not present
        in the dict or set to None are left unchanged.

        Args:
            config_id: The UUID of the config to update.
            data: A dict of field names to new values.

        Returns:
            The updated ReminderConfig if found, or None if not found.
        """
        result = await self.session.execute(
            select(ReminderConfig).where(ReminderConfig.id == config_id)
        )
        config = result.scalar_one_or_none()
        if not config:
            return None
        for key, value in data.items():
            if hasattr(config, key) and value is not None:
                setattr(config, key, value)
        await self.session.flush()
        return config

    async def list_history(self, school_id: str) -> list[ReminderHistory]:
        """Retrieve all reminder history entries for a school.

        Args:
            school_id: The school to scope history to.

        Returns:
            A list of ReminderHistory objects ordered by sent_at descending.
        """
        result = await self.session.execute(
            select(ReminderHistory)
            .where(ReminderHistory.school_id == school_id)
            .order_by(ReminderHistory.sent_at.desc())
        )
        return list(result.scalars().all())
