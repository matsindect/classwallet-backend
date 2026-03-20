"""Pydantic schemas for the authentication module.

Contains request and response models used by the auth router for login,
logout, and user-profile endpoints.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    """Request body for the login endpoint.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password (validated server-side).
    """

    email: EmailStr
    password: str


class UserResponse(BaseModel):
    """Public representation of a user returned by the API.

    Excludes sensitive fields such as ``password_hash`` and
    ``token_version``.

    Attributes:
        id: Unique user identifier.
        school_id: The school this user belongs to.
        email: User email address.
        phone: Optional phone number.
        first_name: User's first name.
        last_name: User's last name.
        role: Role display name (e.g. ``"ADMIN"``).
        role_id: UUID of the assigned role.
        permissions: List of permission action strings.
        is_active: Whether the account is enabled.
        created_at: Account creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: str
    school_id: str | None = None
    email: str
    phone: str | None = None
    first_name: str
    last_name: str
    role: str
    role_id: str
    permissions: list[str] = []
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """Build a UserResponse from a User ORM instance with loaded role."""
        permissions = [
            rp.permission.action for rp in user.role_obj.role_permissions
        ]
        return cls(
            id=user.id,
            school_id=user.school_id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role_obj.name,
            role_id=user.role_id,
            permissions=permissions,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )


class LoginResponse(BaseModel):
    """Response returned on successful authentication.

    Attributes:
        user: Public user profile.
        token: Signed JWT access token.
    """

    user: UserResponse
    token: str
