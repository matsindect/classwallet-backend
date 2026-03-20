"""Business-logic layer for RBAC role and permission management.

Coordinates role CRUD, permission assignment, and enforces constraints
such as preventing deletion of system roles or roles with assigned users.
"""

import re

from app.core.errors import ConflictError, ForbiddenError, NotFoundError, ValidationError
from app.modules.audit.repository import AuditRepository
from app.modules.rbac.models import Role
from app.modules.rbac.repository import RBACRepository


def _slugify(name: str) -> str:
    """Convert a role name to a URL-safe slug."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class RBACService:
    """Service encapsulating RBAC management logic.

    Args:
        repo: Repository for RBAC persistence operations.
        audit_repo: Repository for writing audit-log entries.
    """

    def __init__(self, repo: RBACRepository, audit_repo: AuditRepository):
        self.repo = repo
        self.audit_repo = audit_repo

    async def list_roles(self, school_id: str) -> list[Role]:
        return await self.repo.get_roles_by_school(school_id)

    async def get_role(self, role_id: str) -> Role:
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundError(message="Role not found")
        return role

    async def create_role(
        self,
        school_id: str,
        name: str,
        description: str | None,
        permission_ids: list[str],
        actor_id: str,
    ) -> Role:
        slug = _slugify(name)
        if not slug:
            raise ValidationError(message="Role name is invalid")

        existing = await self.repo.get_role_by_slug_and_school(slug, school_id)
        if existing:
            raise ConflictError(message="A role with this name already exists for this school")

        # Validate all permission IDs exist
        permissions = await self.repo.get_permissions_by_ids(permission_ids)
        if len(permissions) != len(permission_ids):
            raise ValidationError(message="One or more permission IDs are invalid")

        role = Role(
            name=name,
            slug=slug,
            description=description,
            school_id=school_id,
            is_system=False,
        )
        role = await self.repo.create_role(role)
        await self.repo.set_role_permissions(role.id, permission_ids)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="role",
            entity_id=role.id,
        )

        # Re-fetch to get permissions loaded
        return await self.repo.get_role_by_id(role.id)  # type: ignore[return-value]

    async def update_role(
        self,
        role_id: str,
        name: str | None,
        description: str | None,
        permission_ids: list[str] | None,
        school_id: str,
        actor_id: str,
    ) -> Role:
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundError(message="Role not found")

        # School-scoped roles can only be edited by their school
        if role.school_id is not None and role.school_id != school_id:
            raise ForbiddenError(message="Cannot modify a role belonging to another school")

        update_data = {}
        if name is not None:
            slug = _slugify(name)
            if not slug:
                raise ValidationError(message="Role name is invalid")
            # Check slug uniqueness within scope
            existing = await self.repo.get_role_by_slug_and_school(slug, role.school_id)
            if existing and existing.id != role_id:
                raise ConflictError(message="A role with this name already exists")
            update_data["name"] = name
            update_data["slug"] = slug

        if description is not None:
            update_data["description"] = description

        if update_data:
            await self.repo.update_role(role_id, update_data)

        if permission_ids is not None:
            permissions = await self.repo.get_permissions_by_ids(permission_ids)
            if len(permissions) != len(permission_ids):
                raise ValidationError(message="One or more permission IDs are invalid")
            await self.repo.set_role_permissions(role_id, permission_ids)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="role",
            entity_id=role_id,
        )

        return await self.repo.get_role_by_id(role_id)  # type: ignore[return-value]

    async def delete_role(
        self, role_id: str, school_id: str, actor_id: str
    ) -> None:
        role = await self.repo.get_role_by_id(role_id)
        if not role:
            raise NotFoundError(message="Role not found")

        if role.is_system:
            raise ForbiddenError(message="Cannot delete a system role")

        if role.school_id is not None and role.school_id != school_id:
            raise ForbiddenError(message="Cannot delete a role belonging to another school")

        user_count = await self.repo.count_users_with_role(role_id)
        if user_count > 0:
            raise ConflictError(
                message=f"Cannot delete role: {user_count} user(s) are still assigned to it"
            )

        await self.repo.delete_role(role_id)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="delete",
            entity="role",
            entity_id=role_id,
        )

    async def list_permissions(self):
        return await self.repo.get_all_permissions()

    async def create_permission(
        self, action: str, description: str | None, actor_id: str
    ):
        from app.modules.rbac.models import Permission

        existing = await self.repo.get_permission_by_action(action)
        if existing:
            raise ConflictError(message=f"Permission '{action}' already exists")

        permission = Permission(action=action, description=description)
        permission = await self.repo.create_permission(permission)

        await self.audit_repo.log(
            school_id=None,
            actor_id=actor_id,
            action="create",
            entity="permission",
            entity_id=permission.id,
        )
        return permission
