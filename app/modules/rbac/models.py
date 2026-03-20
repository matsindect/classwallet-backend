"""RBAC models for dynamic role and permission management.

Defines the SQLAlchemy ORM models for roles, permissions, and their
many-to-many relationship.  Roles can be system-wide (school_id IS NULL)
or scoped to a specific school.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Permission(Base):
    """A single permission action that can be assigned to roles.

    Attributes:
        id: UUID primary key.
        action: Unique action string (e.g. ``"manage_users"``).
        description: Human-readable description of the permission.
        created_at: Timestamp of creation (UTC).
    """

    __tablename__ = "permissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    action: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )


class Role(Base):
    """A named role that groups permissions.

    System roles (``is_system=True``) are created during migration and
    cannot be deleted.  School-scoped roles have a non-null ``school_id``.

    Attributes:
        id: UUID primary key.
        name: Display name (e.g. ``"ADMIN"``).
        slug: URL-safe normalised name (e.g. ``"admin"``).
        description: Optional description.
        school_id: Foreign key to schools; NULL for system-wide roles.
        is_system: Whether this role is a protected system default.
        created_at: Timestamp of creation (UTC).
        updated_at: Timestamp of last modification (UTC).
        role_permissions: Relationship to :class:`RolePermission` entries.
    """

    __tablename__ = "roles"
    __table_args__ = (UniqueConstraint("slug", "school_id", name="uq_role_slug_school"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    slug: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    school_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("schools.id"), nullable=True
    )
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission", back_populates="role", cascade="all, delete-orphan", lazy="joined"
    )


class RolePermission(Base):
    """Association between a role and a permission.

    Attributes:
        id: UUID primary key.
        role_id: Foreign key to roles.
        permission_id: Foreign key to permissions.
        role: Relationship back to :class:`Role`.
        permission: Relationship to :class:`Permission`.
    """

    __tablename__ = "role_permissions"
    __table_args__ = (UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id", ondelete="CASCADE"), nullable=False
    )
    permission_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("permissions.id", ondelete="CASCADE"), nullable=False
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship("Permission", lazy="joined")
