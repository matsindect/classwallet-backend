"""FastAPI router for reminder endpoints.

Exposes CRUD endpoints for reminder configurations and a read-only
endpoint for reminder dispatch history. All endpoints enforce
role-based access control via policy.enforce() and wrap responses
with the uniform success_response envelope.

Paths align with the frontend API contract:
    GET    /reminders/configs
    POST   /reminders/configs
    PATCH  /reminders/configs/:id
    GET    /reminders/history
"""

from fastapi import APIRouter, Depends

from app.core.di import get_reminder_service
from app.core.policy import enforce
from app.core.response import success_response
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


@router.get("/configs")
async def list_configs(
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """List all reminder configurations for the current user's school.

    Requires the ``reminders.read`` permission.
    """
    enforce(current_user, "reminders.read")
    configs = await service.list_configs(current_user.school_id)
    data = [ReminderConfigResponse.from_model(c).model_dump(by_alias=True) for c in configs]
    return success_response(data=data)


@router.post("/configs", status_code=201)
async def create_config(
    body: ReminderConfigCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """Create a new reminder configuration.

    Requires the ``reminders.create`` permission.
    """
    enforce(current_user, "reminders.create")
    config = await service.create_config(
        school_id=current_user.school_id,
        data=body.model_dump(exclude_unset=True, by_alias=False),
        actor_id=current_user.id,
    )
    data = ReminderConfigResponse.from_model(config).model_dump(by_alias=True)
    return success_response(data=data)


@router.patch("/configs/{config_id}")
async def update_config(
    config_id: str,
    body: ReminderConfigUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """Partially update an existing reminder configuration.

    Requires the ``reminders.update`` permission.
    """
    enforce(current_user, "reminders.update")
    config = await service.update_config(
        config_id=config_id,
        data=body.model_dump(exclude_unset=True, by_alias=False),
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    data = ReminderConfigResponse.from_model(config).model_dump(by_alias=True)
    return success_response(data=data)


@router.get("/history")
async def list_history(
    current_user: UserResponse = Depends(get_current_user),
    service: ReminderService = Depends(get_reminder_service),
):
    """List all reminder dispatch history for the current user's school.

    Requires the ``reminders.read`` permission.
    """
    enforce(current_user, "reminders.read")
    history = await service.list_history(current_user.school_id)
    data = [ReminderHistoryResponse.from_model(h).model_dump(by_alias=True) for h in history]
    return success_response(data=data)
