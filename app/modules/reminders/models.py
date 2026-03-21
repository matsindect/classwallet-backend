"""SQLAlchemy models for the reminders module.

Defines ORM models for reminder configuration templates and the history
of reminders sent to students regarding upcoming invoice due dates.
"""

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ReminderConfig(Base):
    """Configuration template for automated payment reminders.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the owning school.
        name: Human-readable name for the reminder configuration.
        type: Legacy notification channel type (kept for backward compat).
        timing: When the reminder fires relative to due date
                (BEFORE_DUE, ON_DUE, AFTER_DUE).
        channels_json: JSON array of channels, e.g. '["SMS","EMAIL"]'.
        audience: Target audience scope — ALL, GRADE, or CUSTOM.
        grades_json: JSON array of grade names when audience is GRADE.
        student_ids_json: JSON array of student IDs when audience is CUSTOM.
        template: Legacy message template column (kept for backward compat).
        message_template: Message template body with placeholders.
        days_before_due: Legacy days-before-due column (kept for backward compat).
        days_offset: Number of days offset relative to due date.
        is_active: Whether this configuration is currently enabled.
        created_at: Timestamp when the config was created.
        updated_at: Timestamp when the config was last modified.
    """

    __tablename__ = "reminder_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Legacy column kept for backward compatibility
    type: Mapped[str] = mapped_column(String(50), default="email")

    # New columns aligned with frontend contract
    timing: Mapped[str | None] = mapped_column(String(20), nullable=True)
    channels_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[str] = mapped_column(String(20), default="ALL")
    grades_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    student_ids_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Legacy column kept for backward compatibility
    template: Mapped[str | None] = mapped_column(Text, nullable=True)
    # New column aligned with frontend contract
    message_template: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Legacy column kept for backward compatibility
    days_before_due: Mapped[int] = mapped_column(Integer, default=7)
    # New column aligned with frontend contract
    days_offset: Mapped[int | None] = mapped_column(Integer, nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )


class ReminderHistory(Base):
    """Record of a reminder batch sent to students.

    Captures the outcome of a reminder dispatch, linking it back to the
    configuration that triggered it and aggregation counts.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the school.
        reminder_config_id: Foreign key to the ReminderConfig that triggered this.
        student_id: Legacy FK to individual student (kept for backward compat).
        invoice_id: Optional foreign key to the related invoice.
        status: Delivery status (e.g., "sent", "failed").
        config_name: Snapshot of the config name at time of send.
        recipient_count: Total number of recipients targeted.
        delivered_count: Number of successfully delivered reminders.
        failed_count: Number of failed deliveries.
        channels_json: JSON array of channels used, e.g. '["SMS","EMAIL"]'.
        sent_at: Timestamp when the reminder was dispatched.
    """

    __tablename__ = "reminder_history"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    reminder_config_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("reminder_configs.id"), nullable=False
    )
    # Legacy column kept for backward compatibility
    student_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("students.id"), nullable=True
    )
    invoice_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="sent")

    # New columns for aggregation aligned with frontend contract
    config_name: Mapped[str | None] = mapped_column(String(200), nullable=True)
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    delivered_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    channels_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC)
    )
