"""Pydantic schemas for the reminders module.

Defines request and response models for reminder configuration CRUD
operations and reminder history listing. All schemas use CamelModel
for automatic camelCase serialization.
"""

from __future__ import annotations

import json
from datetime import datetime

from app.core.schemas import CamelModel


def _parse_json_list(raw: str | None) -> list[str] | None:
    """Parse a JSON string into a list of strings, returning None on failure."""
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


class ReminderConfigCreate(CamelModel):
    """Schema for creating a new reminder configuration.

    Attributes:
        name: Human-readable name for the reminder.
        timing: When to fire relative to due date (BEFORE_DUE, ON_DUE, AFTER_DUE).
        days_offset: Number of days offset from the due date.
        channels: List of notification channels (SMS, WHATSAPP, EMAIL).
        audience: Target scope — ALL, GRADE, or CUSTOM.
        grades: List of grade names when audience is GRADE.
        student_ids: List of student IDs when audience is CUSTOM.
        message_template: Message body with placeholders.
    """

    name: str
    timing: str
    days_offset: int
    channels: list[str]
    audience: str
    grades: list[str] | None = None
    student_ids: list[str] | None = None
    message_template: str


class ReminderConfigUpdate(CamelModel):
    """Schema for partially updating an existing reminder configuration.

    All fields are optional; only explicitly set fields are applied.
    """

    name: str | None = None
    timing: str | None = None
    days_offset: int | None = None
    channels: list[str] | None = None
    audience: str | None = None
    grades: list[str] | None = None
    student_ids: list[str] | None = None
    message_template: str | None = None
    is_active: bool | None = None


class ReminderConfigResponse(CamelModel):
    """Response schema for a reminder configuration record.

    Uses a ``from_model`` classmethod to parse JSON-encoded fields from
    the ORM model into proper Python lists.
    """

    id: str
    name: str
    timing: str | None = None
    days_offset: int
    channels: list[str]
    audience: str
    grades: list[str] | None = None
    student_ids: list[str] | None = None
    message_template: str | None = None
    is_active: bool
    created_at: datetime

    @classmethod
    def from_model(cls, model: object) -> ReminderConfigResponse:
        """Build a response from a ReminderConfig ORM instance.

        Parses channels_json, grades_json, and student_ids_json into
        Python lists. Falls back to legacy columns when new ones are empty.
        """
        # Resolve days_offset: prefer new column, fall back to legacy
        days_offset = getattr(model, "days_offset", None)
        if days_offset is None:
            days_offset = getattr(model, "days_before_due", 0)

        # Resolve message_template: prefer new column, fall back to legacy
        message_template = getattr(model, "message_template", None) or getattr(
            model, "template", None
        )

        # Resolve timing: fall back to legacy type column if timing is empty
        timing = getattr(model, "timing", None) or getattr(model, "type", None)

        channels = _parse_json_list(getattr(model, "channels_json", None)) or []

        return cls(
            id=model.id,
            name=model.name,
            timing=timing,
            days_offset=days_offset,
            channels=channels,
            audience=getattr(model, "audience", "ALL"),
            grades=_parse_json_list(getattr(model, "grades_json", None)),
            student_ids=_parse_json_list(getattr(model, "student_ids_json", None)),
            message_template=message_template,
            is_active=model.is_active,
            created_at=model.created_at,
        )


class ReminderHistoryResponse(CamelModel):
    """Response schema for a reminder history entry."""

    id: str
    config_id: str
    config_name: str | None = None
    sent_at: datetime
    recipient_count: int
    delivered_count: int
    failed_count: int
    channels: list[str]

    @classmethod
    def from_model(cls, model: object) -> ReminderHistoryResponse:
        """Build a response from a ReminderHistory ORM instance.

        Parses channels_json into a Python list.
        """
        return cls(
            id=model.id,
            config_id=model.reminder_config_id,
            config_name=getattr(model, "config_name", None),
            sent_at=model.sent_at,
            recipient_count=getattr(model, "recipient_count", 0),
            delivered_count=getattr(model, "delivered_count", 0),
            failed_count=getattr(model, "failed_count", 0),
            channels=_parse_json_list(getattr(model, "channels_json", None)) or [],
        )
