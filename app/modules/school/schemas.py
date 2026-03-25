"""Pydantic schemas for the school module.

Contains request and response models for school profile management and
school-scoped user administration endpoints.  All schemas inherit from
``CamelModel`` for automatic camelCase serialisation.
"""

import json
from datetime import datetime
from typing import Any

from pydantic import EmailStr, field_validator

from app.core.schemas import CamelModel


class SchoolResponse(CamelModel):
    """Public representation of a school returned by the API."""

    id: str
    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    receipt_footer: str | None = None
    merchant_code: str | None = None
    biller_code: str | None = None
    account_identifier: str | None = None
    academic_term_config: dict[str, Any] | None = None
    currency: str
    timezone: str
    created_at: datetime

    @field_validator("academic_term_config", mode="before")
    @classmethod
    def parse_academic_term_config(cls, v: Any) -> dict[str, Any] | None:
        """Parse a JSON string from the DB into a dict."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        return v


class SchoolCreate(CamelModel):
    """Request body for creating/onboarding a new school."""

    name: str
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    currency: str = "USD"
    timezone: str = "UTC"


class SchoolUpdate(CamelModel):
    """Request body for partially updating a school's profile.

    All fields are optional; only fields that are explicitly set will be
    applied.
    """

    name: str | None = None
    address: str | None = None
    city: str | None = None
    state: str | None = None
    country: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    logo_url: str | None = None
    receipt_footer: str | None = None
    merchant_code: str | None = None
    biller_code: str | None = None
    account_identifier: str | None = None
    academic_term_config: dict[str, Any] | None = None
    currency: str | None = None
    timezone: str | None = None


class SchoolUserResponse(CamelModel):
    """Public representation of a school user returned by the API."""

    id: str
    email: str
    phone: str | None = None
    first_name: str
    last_name: str
    role: str
    is_active: bool
    invited_at: datetime
    last_login_at: datetime | None = None

    @classmethod
    def from_user(cls, user: Any) -> "SchoolUserResponse":
        """Build from a User ORM instance with loaded role."""
        return cls(
            id=user.id,
            email=user.email,
            phone=user.phone,
            first_name=user.first_name,
            last_name=user.last_name,
            role=user.role_obj.name,
            is_active=user.is_active,
            invited_at=user.created_at,
            last_login_at=user.last_login_at,
        )


class SchoolUserCreate(CamelModel):
    """Request body for creating a new user within a school."""

    email: EmailStr
    phone: str | None = None
    first_name: str
    last_name: str
    role: str


class SchoolUserUpdate(CamelModel):
    """Request body for partially updating a school user."""

    first_name: str | None = None
    last_name: str | None = None
    phone: str | None = None
    role: str | None = None
    is_active: bool | None = None
