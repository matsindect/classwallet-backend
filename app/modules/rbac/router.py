"""FastAPI router for RBAC management endpoints.

Exposes endpoints for listing/creating/updating/deleting roles and
listing available permissions. All endpoints require authentication
and the ``manage_roles`` permission.
"""

from fastapi import APIRouter, Depends

from app.core.di import get_rbac_service
from app.core.policy import enforce
from app.modules.auth.dependencies import require_school_user
from app.modules.auth.schemas import UserResponse
from app.modules.rbac.schemas import (
    PermissionCreate,
    PermissionResponse,
    RoleCreate,
    RoleResponse,
    RoleUpdate,
)
from app.modules.rbac.service import RBACService

router = APIRouter(prefix="/roles", tags=["Roles & Permissions"])


def _role_to_response(role) -> RoleResponse:
    """Map a Role ORM instance to a RoleResponse with nested permissions."""
    permissions = [PermissionResponse.model_validate(rp.permission) for rp in role.role_permissions]
    return RoleResponse(
        id=role.id,
        name=role.name,
        slug=role.slug,
        description=role.description,
        school_id=role.school_id,
        is_system=role.is_system,
        permissions=permissions,
        created_at=role.created_at,
        updated_at=role.updated_at,
    )


@router.get("", response_model=list[RoleResponse])
async def list_roles(
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """List all roles available to the current school.

    Returns system-wide roles and school-scoped roles.
    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "roles.read")
    roles = await service.list_roles(current_user.school_id)
    return [_role_to_response(r) for r in roles]


@router.post("", response_model=RoleResponse, status_code=201)
async def create_role(
    body: RoleCreate,
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """Create a new school-scoped role.

    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "roles.create")
    role = await service.create_role(
        school_id=current_user.school_id,
        name=body.name,
        description=body.description,
        permission_ids=body.permissionIds,
        actor_id=current_user.id,
    )
    return _role_to_response(role)


@router.get("/permissions", response_model=list[PermissionResponse])
async def list_permissions(
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """List all available permissions.

    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "permissions.read")
    permissions = await service.list_permissions()
    return [PermissionResponse.model_validate(p) for p in permissions]


@router.post("/permissions", response_model=PermissionResponse, status_code=201)
async def create_permission(
    body: PermissionCreate,
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """Create a new permission.

    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "permissions.create")
    permission = await service.create_permission(
        action=body.action,
        description=body.description,
        actor_id=current_user.id,
    )
    return PermissionResponse.model_validate(permission)


@router.get("/{role_id}", response_model=RoleResponse)
async def get_role(
    role_id: str,
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """Get a single role with its permissions.

    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "roles.read")
    role = await service.get_role(role_id)
    return _role_to_response(role)


@router.patch("/{role_id}", response_model=RoleResponse)
async def update_role(
    role_id: str,
    body: RoleUpdate,
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """Update a role's name, description, or permissions.

    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "roles.update")
    role = await service.update_role(
        role_id=role_id,
        name=body.name,
        description=body.description,
        permission_ids=body.permissionIds,
        school_id=current_user.school_id,
        actor_id=current_user.id,
    )
    return _role_to_response(role)


@router.delete("/{role_id}", status_code=204)
async def delete_role(
    role_id: str,
    current_user: UserResponse = Depends(require_school_user),
    service: RBACService = Depends(get_rbac_service),
):
    """Delete a non-system role.

    Fails if the role is a system role or has users assigned.
    Requires the ``manage_roles`` permission.
    """
    enforce(current_user, "roles.delete")
    await service.delete_role(
        role_id=role_id,
        school_id=current_user.school_id,
        actor_id=current_user.id,
    )
