"""Pydantic schemas for the authentication module.

Contains request and response models used by the auth router for login,
logout, and user-profile endpoints.  All schemas inherit from
``CamelModel`` so field names are serialised as camelCase.
"""

from datetime import datetime

from pydantic import EmailStr

from app.core.schemas import CamelModel

# ---------------------------------------------------------------------------
# Role → UI permission mapping (for frontend display only, not RBAC enforcement)
# ---------------------------------------------------------------------------
ROLE_UI_PERMISSIONS: dict[str, list[str]] = {
    "SUPER_ADMIN": [
        "schools.*",
        "users.*",
        "students.*",
        "fees.*",
        "invoices.*",
        "payments.*",
        "reminders.*",
        "reports.*",
        "audit.*",
        "roles.*",
        "permissions.*",
    ],
    "ADMIN": [
        "school.*",
        "users.*",
        "students.*",
        "fees.*",
        "invoices.*",
        "payments.*",
        "reminders.*",
        "reports.*",
        "audit.*",
        "roles.*",
        "permissions.*",
    ],
    "FINANCE": [
        "fees.*",
        "invoices.*",
        "payments.*",
        "reminders.*",
        "reports.*",
    ],
    "STAFF": [
        "students.read",
        "payments.read",
    ],
}


def permissions_for_role(role_name: str) -> list[str]:
    """Return the UI permission strings for a given role name."""
    return ROLE_UI_PERMISSIONS.get(role_name, [])


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class LoginRequest(CamelModel):
    """Request body for the login endpoint.

    Attributes:
        email: The user's email address.
        password: The user's plaintext password (validated server-side).
    """

    email: EmailStr
    password: str


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(CamelModel):
    """Public representation of a user returned by the API.

    Matches the frontend contract: includes role-based UI permissions,
    ``avatarUrl``, and ``lastLoginAt``.  Excludes sensitive fields such
    as ``password_hash`` and ``token_version``.
    """

    model_config = {"from_attributes": True}

    id: str
    email: str
    phone: str | None = None
    first_name: str
    last_name: str
    role: str
    permissions: list[str] = []
    avatar_url: str | None = None
    school_id: str | None = None
    is_active: bool
    created_at: datetime
    last_login_at: datetime | None = None

    @classmethod
    def from_user(cls, user) -> "UserResponse":
        """Build a ``UserResponse`` from a User ORM instance with loaded role."""
        role_name = user.role_obj.name if user.role_obj else (user.role or "")
        return cls(
            id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=role_name,
            permissions=permissions_for_role(role_name),
            avatar_url=user.avatar_url,
            school_id=user.school_id,
            is_active=user.is_active,
            created_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class LoginData(CamelModel):
    """Wrapper returned inside the envelope ``data`` field on login.

    Attributes:
        user: Public user profile.
        token: Signed JWT access token.
    """

    user: UserResponse
    token: str
