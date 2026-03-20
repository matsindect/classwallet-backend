"""Service layer for reminder business logic.

Orchestrates CRUD operations on reminder configurations and retrieval
of reminder history, with audit logging for create and update actions.
"""

from app.core.errors import NotFoundError
from app.modules.audit.repository import AuditRepository
from app.modules.reminders.models import ReminderConfig, ReminderHistory
from app.modules.reminders.repository import ReminderRepository


class ReminderService:
    """Business logic service for reminder operations.

    Manages reminder configuration lifecycle (list, create, update) and
    provides access to reminder dispatch history. All mutating operations
    are recorded in the audit log.

    Args:
        repo: Repository for reminder data access.
        audit_repo: Repository for writing audit log entries.
    """

    def __init__(self, repo: ReminderRepository, audit_repo: AuditRepository):
        self.repo = repo
        self.audit_repo = audit_repo

    async def list_configs(self, school_id: str) -> list[ReminderConfig]:
        """List all reminder configurations for a school.

        Args:
            school_id: The school to scope configs to.

        Returns:
            A list of ReminderConfig objects.
        """
        return await self.repo.list_configs(school_id)

    async def create_config(self, school_id: str, data: dict, actor_id: str) -> ReminderConfig:
        """Create a new reminder configuration.

        Persists the configuration and writes an audit log entry recording
        the creation.

        Args:
            school_id: The school to associate the config with.
            data: Dict of configuration fields to set.
            actor_id: The ID of the user performing the action.

        Returns:
            The newly created ReminderConfig.
        """
        config = ReminderConfig(school_id=school_id, **data)
        config = await self.repo.create_config(config)
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="reminder_config",
            entity_id=config.id,
        )
        return config

    async def update_config(
        self, config_id: str, data: dict, actor_id: str, school_id: str
    ) -> ReminderConfig:
        """Update an existing reminder configuration.

        Applies partial updates and writes an audit log entry recording
        the modification.

        Args:
            config_id: The UUID of the config to update.
            data: Dict of fields to update (only non-None values applied).
            actor_id: The ID of the user performing the action.
            school_id: The school the config belongs to.

        Returns:
            The updated ReminderConfig.

        Raises:
            NotFoundError: If no config with the given ID exists.
        """
        config = await self.repo.update_config(config_id, data)
        if not config:
            raise NotFoundError(message="Reminder config not found")
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="reminder_config",
            entity_id=config_id,
        )
        return config

    async def list_history(self, school_id: str) -> list[ReminderHistory]:
        """List all reminder history entries for a school.

        Args:
            school_id: The school to scope history to.

        Returns:
            A list of ReminderHistory objects.
        """
        return await self.repo.list_history(school_id)
