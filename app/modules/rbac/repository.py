"""Data-access layer for RBAC role and permission management.

Provides CRUD operations on the ``roles``, ``permissions``, and
``role_permissions`` tables.  All methods flush but do not commit.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.modules.rbac.models import Permission, Role, RolePermission


class RBACRepository:
    """Repository handling persistence for RBAC entities.

    Args:
        session: An active SQLAlchemy async session.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # --- Roles ---

    async def get_role_by_id(self, role_id: str) -> Role | None:
        result = await self.session.execute(
            select(Role)
            .options(
                joinedload(Role.role_permissions).joinedload(RolePermission.permission)
            )
            .where(Role.id == role_id)
        )
        return result.unique().scalar_one_or_none()

    async def get_roles_by_school(self, school_id: str) -> list[Role]:
        """Return system roles and school-scoped roles for the given school."""
        result = await self.session.execute(
            select(Role)
            .options(
                joinedload(Role.role_permissions).joinedload(RolePermission.permission)
            )
            .where((Role.school_id.is_(None)) | (Role.school_id == school_id))
            .order_by(Role.is_system.desc(), Role.name)
        )
        return list(result.unique().scalars().all())

    async def get_role_by_slug_and_school(
        self, slug: str, school_id: str | None
    ) -> Role | None:
        result = await self.session.execute(
            select(Role).where(Role.slug == slug, Role.school_id == school_id)
        )
        return result.scalar_one_or_none()

    async def create_role(self, role: Role) -> Role:
        self.session.add(role)
        await self.session.flush()
        return role

    async def update_role(self, role_id: str, data: dict) -> Role | None:
        role = await self.get_role_by_id(role_id)
        if not role:
            return None
        for key, value in data.items():
            if hasattr(role, key) and value is not None:
                setattr(role, key, value)
        await self.session.flush()
        return role

    async def delete_role(self, role_id: str) -> bool:
        role = await self.get_role_by_id(role_id)
        if not role:
            return False
        await self.session.delete(role)
        await self.session.flush()
        return True

    async def count_users_with_role(self, role_id: str) -> int:
        from app.modules.auth.models import User

        result = await self.session.execute(
            select(func.count()).select_from(User).where(User.role_id == role_id)
        )
        return result.scalar_one()

    # --- Permissions ---

    async def get_all_permissions(self) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).order_by(Permission.action)
        )
        return list(result.scalars().all())

    async def get_permission_by_action(self, action: str) -> Permission | None:
        result = await self.session.execute(
            select(Permission).where(Permission.action == action)
        )
        return result.scalar_one_or_none()

    async def get_permissions_by_ids(self, permission_ids: list[str]) -> list[Permission]:
        result = await self.session.execute(
            select(Permission).where(Permission.id.in_(permission_ids))
        )
        return list(result.scalars().all())

    async def create_permission(self, permission: Permission) -> Permission:
        self.session.add(permission)
        await self.session.flush()
        return permission

    # --- Role-Permission assignments ---

    async def set_role_permissions(
        self, role_id: str, permission_ids: list[str]
    ) -> None:
        """Replace all permissions for a role with the given set."""
        await self.session.execute(
            delete(RolePermission).where(RolePermission.role_id == role_id)
        )
        for perm_id in permission_ids:
            self.session.add(
                RolePermission(role_id=role_id, permission_id=perm_id)
            )
        await self.session.flush()
