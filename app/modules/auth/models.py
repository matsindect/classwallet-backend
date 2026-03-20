"""Authentication models for the User entity.

Defines the SQLAlchemy ORM model for application users, including
credentials, role assignments, and token-version-based session
invalidation.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class User(Base):
    """Represents an application user belonging to a school.

    Each user is linked to a :class:`~app.modules.rbac.models.Role` via
    ``role_id``, which determines their permissions.  The ``role`` string
    column is retained temporarily for migration compatibility and will
    be removed in a future migration.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key linking the user to a school.
        email: Unique email address used for login.
        phone: Optional phone number.
        first_name: User's first name.
        last_name: User's last name.
        password_hash: Bcrypt hash of the user's password.
        role: Legacy role string column (nullable, kept for migration).
        role_id: Foreign key to the roles table.
        role_obj: Relationship to the :class:`Role` model.
        is_active: Whether the account is enabled.
        token_version: Monotonically increasing counter for JWT revocation.
        created_at: Timestamp of account creation (UTC).
        updated_at: Timestamp of last modification (UTC).
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("schools.id"), nullable=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    first_name: Mapped[str] = mapped_column(String(100), nullable=False)
    last_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(String(20), nullable=True)
    role_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("roles.id"), nullable=False
    )
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    token_version: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    role_obj: Mapped["app.modules.rbac.models.Role"] = relationship(  # noqa: F821
        "Role", lazy="joined"
    )
