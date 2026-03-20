"""Pydantic schemas for the reminders module.

Defines request and response models for reminder configuration CRUD
operations and reminder history listing.
"""

from datetime import datetime

from pydantic import BaseModel


class ReminderConfigCreate(BaseModel):
    """Schema for creating a new reminder configuration.

    All fields are optional to allow partial specification; defaults
    are applied at the model layer.

    Attributes:
        name: Human-readable name for the reminder.
        type: Notification channel type (e.g., "email", "sms").
        template: Optional message template body.
        days_before_due: Days before due date to trigger the reminder.
        is_active: Whether the configuration is enabled.
    """

    name: str | None = None
    type: str | None = None
    template: str | None = None
    days_before_due: int | None = None
    is_active: bool | None = None


class ReminderConfigUpdate(BaseModel):
    """Schema for partially updating an existing reminder configuration.

    Only fields that are explicitly set will be applied to the existing
    record (using ``exclude_unset``).

    Attributes:
        name: Updated name for the reminder.
        type: Updated notification channel type.
        template: Updated message template body.
        days_before_due: Updated days-before-due value.
        is_active: Updated active/inactive flag.
    """

    name: str | None = None
    type: str | None = None
    template: str | None = None
    days_before_due: int | None = None
    is_active: bool | None = None


class ReminderConfigResponse(BaseModel):
    """Response schema for a reminder configuration record.

    Serializes a ReminderConfig ORM model for API responses.

    Attributes:
        id: Unique identifier.
        school_id: Identifier of the owning school.
        name: Human-readable name.
        type: Notification channel type.
        template: Message template body, if set.
        days_before_due: Days before due date to trigger.
        is_active: Whether the configuration is enabled.
        created_at: When the config was created.
        updated_at: When the config was last modified.
    """

    id: str
    school_id: str
    name: str
    type: str
    template: str | None = None
    days_before_due: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ReminderHistoryResponse(BaseModel):
    """Response schema for a reminder history entry.

    Serializes a ReminderHistory ORM model for API responses.

    Attributes:
        id: Unique identifier.
        school_id: Identifier of the school.
        reminder_config_id: Identifier of the config that triggered this.
        student_id: Identifier of the student who received the reminder.
        invoice_id: Identifier of the related invoice, if any.
        status: Delivery status of the reminder.
        sent_at: When the reminder was dispatched.
    """

    id: str
    school_id: str
    reminder_config_id: str
    student_id: str
    invoice_id: str | None = None
    status: str
    sent_at: datetime

    model_config = {"from_attributes": True}
