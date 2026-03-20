"""SQLAlchemy models for the reminders module.

Defines ORM models for reminder configuration templates and the history
of reminders sent to students regarding upcoming invoice due dates.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReminderConfig(Base):
    """Configuration template for automated payment reminders.

    Stores the settings that determine how and when reminders are sent,
    including the notification type, message template, and how many days
    before a due date the reminder should trigger.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the owning school.
        name: Human-readable name for the reminder configuration.
        type: Notification channel type (e.g., "email", "sms").
        template: Optional message template body.
        days_before_due: Number of days before the due date to send.
        is_active: Whether this configuration is currently enabled.
        created_at: Timestamp when the config was created.
        updated_at: Timestamp when the config was last modified.
    """
    __tablename__ = "reminder_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), default="email")
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    days_before_due: Mapped[int] = mapped_column(Integer, default=7)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


class ReminderHistory(Base):
    """Record of an individual reminder sent to a student.

    Captures the outcome of a reminder dispatch, linking it back to the
    configuration that triggered it and the target student/invoice.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the school.
        reminder_config_id: Foreign key to the ReminderConfig that triggered this.
        student_id: Foreign key to the student who received the reminder.
        invoice_id: Optional foreign key to the related invoice.
        status: Delivery status (e.g., "sent", "failed").
        sent_at: Timestamp when the reminder was dispatched.
    """
    __tablename__ = "reminder_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    reminder_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reminder_configs.id"), nullable=False
    )
    student_id: Mapped[str] = mapped_column(String(36), ForeignKey("students.id"), nullable=False)
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent")
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
