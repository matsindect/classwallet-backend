"""School API router.

Exposes endpoints for retrieving and updating the school profile, as
well as managing school users (list, create, update).  User management
endpoints delegate to :class:`~app.modules.auth.service.AuthService`
since users are an auth-module entity.  All mutating endpoints enforce
role-based access via :func:`~app.core.policy.enforce`.
"""

import json

from fastapi import APIRouter, Depends

from app.core.di import get_auth_service, get_school_service
from app.core.policy import enforce
from app.core.response import success_response
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.auth.service import AuthService
from app.modules.school.schemas import (
    SchoolResponse,
    SchoolUpdate,
    SchoolUserCreate,
    SchoolUserResponse,
    SchoolUserUpdate,
)
from app.modules.school.service import SchoolService

router = APIRouter(prefix="/school", tags=["School"])


@router.get("")
async def get_school(
    current_user: UserResponse = Depends(get_current_user),
    service: SchoolService = Depends(get_school_service),
):
    """Retrieve the current user's school profile."""
    school = await service.get_school(current_user.school_id)
    data = SchoolResponse.model_validate(school).model_dump(by_alias=True)
    return success_response(data=data)


@router.patch("")
async def update_school(
    body: SchoolUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: SchoolService = Depends(get_school_service),
):
    """Update the current user's school profile.

    Requires the ``school.update`` permission.
    """
    enforce(current_user, "school.update")
    update_data = body.model_dump(exclude_unset=True)

    # Serialise academic_term_config dict to a JSON string for DB storage.
    if "academic_term_config" in update_data and isinstance(
        update_data["academic_term_config"], dict
    ):
        update_data["academic_term_config"] = json.dumps(update_data["academic_term_config"])

    school = await service.update_school(
        current_user.school_id,
        update_data,
        actor_id=current_user.id,
    )
    data = SchoolResponse.model_validate(school).model_dump(by_alias=True)
    return success_response(data=data)


@router.get("/users")
async def list_users(
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """List all users belonging to the current school.

    Requires the ``users.read`` permission.
    """
    enforce(current_user, "users.read")
    users = await auth_service.get_school_users(current_user.school_id)
    data = [SchoolUserResponse.from_user(u).model_dump(by_alias=True) for u in users]
    return success_response(data=data)


@router.post("/users", status_code=201)
async def create_user(
    body: SchoolUserCreate,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new user within the current school.

    Requires the ``users.create`` permission.
    """
    enforce(current_user, "users.create")
    user = await auth_service.create_school_user(
        school_id=current_user.school_id,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        role_id=body.role,
        phone=body.phone,
        actor_id=current_user.id,
    )
    data = SchoolUserResponse.from_user(user).model_dump(by_alias=True)
    return success_response(data=data)


@router.patch("/users/{user_id}")
async def update_user(
    user_id: str,
    body: SchoolUserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update an existing school user's profile.

    Requires the ``users.update`` permission.
    """
    enforce(current_user, "users.update")
    update_data = {}
    raw = body.model_dump(exclude_unset=True)
    if "first_name" in raw:
        update_data["first_name"] = raw["first_name"]
    if "last_name" in raw:
        update_data["last_name"] = raw["last_name"]
    if "role" in raw:
        update_data["role_id"] = raw["role"]
    for k in ("phone", "is_active"):
        if k in raw:
            update_data[k] = raw[k]

    user = await auth_service.update_school_user(
        user_id=user_id,
        data=update_data,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    data = SchoolUserResponse.from_user(user).model_dump(by_alias=True)
    return success_response(data=data)
