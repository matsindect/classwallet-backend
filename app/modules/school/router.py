"""School API router.

Exposes endpoints for retrieving and updating the school profile, as
well as managing school users (list, create, update).  User management
endpoints delegate to :class:`~app.modules.auth.service.AuthService`
since users are an auth-module entity.  All mutating endpoints enforce
role-based access via :func:`~app.core.policy.enforce`.
"""

from fastapi import APIRouter, Depends

from app.core.di import get_auth_service, get_school_service
from app.core.policy import enforce
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


@router.get("", response_model=SchoolResponse)
async def get_school(
    current_user: UserResponse = Depends(get_current_user),
    service: SchoolService = Depends(get_school_service),
):
    """Retrieve the current user's school profile.

    Args:
        current_user: The authenticated user (used to determine school).
        service: Injected school service.

    Returns:
        The school's ``SchoolResponse`` representation.
    """
    school = await service.get_school(current_user.school_id)
    return SchoolResponse.model_validate(school)


@router.patch("", response_model=SchoolResponse)
async def update_school(
    body: SchoolUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: SchoolService = Depends(get_school_service),
):
    """Update the current user's school profile.

    Requires the ``manage_school`` permission (ADMIN role).

    Args:
        body: Partial school update fields.
        current_user: The authenticated user.
        service: Injected school service.

    Returns:
        The updated ``SchoolResponse``.
    """
    enforce(current_user, "school.update")
    school = await service.update_school(
        current_user.school_id,
        body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return SchoolResponse.model_validate(school)


@router.get("/users", response_model=list[SchoolUserResponse])
async def list_users(
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """List all users belonging to the current school.

    Requires the ``manage_users`` permission.

    Args:
        current_user: The authenticated user.
        auth_service: Injected auth service (owns user data).

    Returns:
        A list of ``SchoolUserResponse`` objects, newest first.
    """
    enforce(current_user, "users.read")
    users = await auth_service.get_school_users(current_user.school_id)
    return [SchoolUserResponse.from_user(u) for u in users]


@router.post("/users", response_model=SchoolUserResponse, status_code=201)
async def create_user(
    body: SchoolUserCreate,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Create a new user within the current school.

    The new user is assigned the default password ``changeme123``.
    Requires the ``manage_users`` permission.

    Args:
        body: New user details (email, name, role).
        current_user: The authenticated user.
        auth_service: Injected auth service.

    Returns:
        The newly created ``SchoolUserResponse``.
    """
    enforce(current_user, "users.create")
    user = await auth_service.create_school_user(
        school_id=current_user.school_id,
        email=body.email,
        first_name=body.firstName,
        last_name=body.lastName,
        role_id=body.roleId,
        phone=body.phone,
        actor_id=current_user.id,
    )
    return SchoolUserResponse.from_user(user)


@router.patch("/users/{user_id}", response_model=SchoolUserResponse)
async def update_user(
    user_id: str,
    body: SchoolUserUpdate,
    current_user: UserResponse = Depends(get_current_user),
    auth_service: AuthService = Depends(get_auth_service),
):
    """Update an existing school user's profile.

    Maps camelCase request fields (``firstName``, ``lastName``) to their
    snake_case ORM equivalents before delegating to the auth service.
    Requires the ``manage_users`` permission.

    Args:
        user_id: UUID of the user to update.
        body: Partial user update fields.
        current_user: The authenticated user.
        auth_service: Injected auth service.

    Returns:
        The updated ``SchoolUserResponse``.
    """
    enforce(current_user, "users.update")
    update_data = {}
    raw = body.model_dump(exclude_unset=True)
    if "firstName" in raw:
        update_data["first_name"] = raw["firstName"]
    if "lastName" in raw:
        update_data["last_name"] = raw["lastName"]
    if "roleId" in raw:
        update_data["role_id"] = raw["roleId"]
    for k in ("phone", "is_active"):
        if k in raw:
            update_data[k] = raw[k]

    user = await auth_service.update_school_user(
        user_id=user_id,
        data=update_data,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return SchoolUserResponse.from_user(user)
