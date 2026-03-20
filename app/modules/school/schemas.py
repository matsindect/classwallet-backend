"""Pydantic schemas for the school module.

Contains request and response models for school profile management and
school-scoped user administration endpoints.  Field names use camelCase
in create/update schemas to match the frontend API contract, while
response schemas use snake_case mapped from ORM attributes.
"""

from datetime import datetime

from pydantic import BaseModel, EmailStr


class SchoolResponse(BaseModel):
    """Public representation of a school returned by the API.

    Attributes:
        id: Unique school identifier.
        name: School display name.
        address: Physical address, if provided.
        phone: Contact phone number, if provided.
        email: Contact email, if provided.
        website: School website URL, if provided.
        logo_url: URL to the school logo, if provided.
        currency: ISO 4217 currency code.
        timezone: IANA timezone identifier.
        created_at: Creation timestamp.
        updated_at: Last modification timestamp.
    """

    id: str
    name: str
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    currency: str
    timezone: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SchoolUpdate(BaseModel):
    """Request body for partially updating a school's profile.

    Only fields that are explicitly set (not ``None``) will be applied.

    Attributes:
        name: New school name.
        address: New address.
        phone: New phone number.
        email: New contact email.
        website: New website URL.
        logo_url: New logo URL.
        currency: New currency code.
        timezone: New timezone identifier.
    """

    name: str | None = None
    address: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    currency: str | None = None
    timezone: str | None = None


class SchoolUserCreate(BaseModel):
    """Request body for creating a new user within a school.

    Uses camelCase field names to match the frontend API contract.
    The new user is assigned the default password ``changeme123``.

    Attributes:
        email: Unique email address for the new user.
        phone: Optional phone number.
        firstName: User's first name.
        lastName: User's last name.
        roleId: UUID of the role to assign.
    """

    email: EmailStr
    phone: str | None = None
    firstName: str  # noqa: N815
    lastName: str  # noqa: N815
    roleId: str  # noqa: N815


class SchoolUserUpdate(BaseModel):
    """Request body for partially updating a school user.

    Uses camelCase field names to match the frontend API contract.
    Only fields that are explicitly set will be applied.

    Attributes:
        phone: New phone number.
        firstName: New first name.
        lastName: New last name.
        roleId: UUID of the new role to assign.
        is_active: Whether the user account should be active.
    """

    phone: str | None = None
    firstName: str | None = None  # noqa: N815
    lastName: str | None = None  # noqa: N815
    roleId: str | None = None  # noqa: N815
    is_active: bool | None = None


class SchoolUserResponse(BaseModel):
    """Public representation of a school user returned by the API.

    Attributes:
        id: Unique user identifier.
        school_id: The school this user belongs to.
        email: User email address.
        phone: Phone number, if provided.
        first_name: User's first name.
        last_name: User's last name.
        role: Role display name.
        role_id: UUID of the assigned role.
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
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_user(cls, user) -> "SchoolUserResponse":
        """Build from a User ORM instance with loaded role."""
        return cls(
            id=user.id,
            school_id=user.school_id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role_obj.name,
            role_id=user.role_id,
            is_active=user.is_active,
            created_at=user.created_at,
            updated_at=user.updated_at,
        )
