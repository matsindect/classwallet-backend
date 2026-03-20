"""FastAPI router for reminder endpoints.

Exposes CRUD endpoints for reminder configurations and a read-only
endpoint for reminder dispatch history. All endpoints enforce
role-based access control via policy.enforce().
"""

from fastapi import APIRouter, Depends

from app.core.di import get_reminder_service
from app.core.policy import enforce
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.reminders.schemas import (
    ReminderConfigCreate,
    ReminderConfigResponse,
    ReminderConfigUpdate,
    ReminderHistoryResponse,
)
from app.modules.reminders.service import ReminderService

router = APIRouter(prefix="/reminders", tags=["Reminders"])


@router.get("/config", response_model=list[ReminderConfigResponse])
async def list_configs(
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """List all reminder configurations for the current user's school.

    Requires the ``manage_reminders`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: The ReminderService instance (injected).

    Returns:
        A list of ReminderConfigResponse objects.
    """
    enforce(current_user, "reminders.read")
    configs = await service.list_configs(current_user.school_id)
    return [ReminderConfigResponse.model_validate(c) for c in configs]


@router.post("/config", response_model=ReminderConfigResponse, status_code=201)
async def create_config(
    body: ReminderConfigCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """Create a new reminder configuration.

    Requires the ``manage_reminders`` permission.

    Args:
        body: The reminder configuration fields to set.
        current_user: The authenticated user (injected).
        service: The ReminderService instance (injected).

    Returns:
        The newly created ReminderConfigResponse.
    """
    enforce(current_user, "reminders.create")
    config = await service.create_config(
        school_id=current_user.school_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return ReminderConfigResponse.model_validate(config)


@router.patch("/config/{config_id}", response_model=ReminderConfigResponse)
async def update_config(
    config_id: str,
    body: ReminderConfigUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """Partially update an existing reminder configuration.

    Requires the ``manage_reminders`` permission.

    Args:
        config_id: The UUID of the configuration to update.
        body: The fields to update (only set fields are applied).
        current_user: The authenticated user (injected).
        service: The ReminderService instance (injected).

    Returns:
        The updated ReminderConfigResponse.

    Raises:
        NotFoundError: If no config with the given ID exists.
    """
    enforce(current_user, "reminders.update")
    config = await service.update_config(
        config_id=config_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return ReminderConfigResponse.model_validate(config)


@router.get("/history", response_model=list[ReminderHistoryResponse])
async def list_history(
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """List all reminder dispatch history for the current user's school.

    Requires the ``manage_reminders`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: The ReminderService instance (injected).

    Returns:
        A list of ReminderHistoryResponse objects.
    """
    enforce(current_user, "reminders.read")
    history = await service.list_history(current_user.school_id)
    return [ReminderHistoryResponse.model_validate(h) for h in history]
