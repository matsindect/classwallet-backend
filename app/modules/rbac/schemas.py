"""Pydantic schemas for the RBAC module.

Contains request and response models for role and permission management.
"""

from datetime import datetime

from pydantic import BaseModel


class PermissionResponse(BaseModel):
    """Public representation of a permission."""

    id: str
    action: str
    description: str | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class RoleResponse(BaseModel):
    """Public representation of a role with its assigned permissions."""

    id: str
    name: str
    slug: str
    description: str | None = None
    school_id: str | None = None
    is_system: bool
    permissions: list[PermissionResponse] = []
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PermissionCreate(BaseModel):
    """Request body for creating a new permission."""

    action: str
    description: str | None = None


class RoleCreate(BaseModel):
    """Request body for creating a new role."""

    name: str
    description: str | None = None
    permissionIds: list[str]  # noqa: N815


class RoleUpdate(BaseModel):
    """Request body for partially updating a role."""

    name: str | None = None
    description: str | None = None
    permissionIds: list[str] | None = None  # noqa: N815
