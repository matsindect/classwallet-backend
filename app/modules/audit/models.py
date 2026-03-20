"""SQLAlchemy models for the audit module.

Defines the AuditLog ORM model that records actions performed across the
application for accountability and traceability purposes.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class AuditLog(Base):
    """Represents an immutable audit trail entry.

    Each entry records who performed an action, what action was taken,
    which entity was affected, and optional metadata as a JSON string.
    Audit logs are written as a cross-cutting concern by services
    throughout the application.

    Attributes:
        id: UUID primary key.
        school_id: Foreign key to the school this log belongs to.
        actor_id: Identifier of the user or system that performed the action.
        action: The action performed (e.g., "create", "update", "reconciliation").
        entity: The type of entity affected (e.g., "payment", "reminder_config").
        entity_id: Optional identifier of the specific entity affected.
        metadata_json: Optional JSON string with additional context.
        timestamp: When the action occurred.
    """
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    school_id: Mapped[str] = mapped_column(String(36), ForeignKey("schools.id"), nullable=False)
    actor_id: Mapped[str] = mapped_column(String(36), nullable=False)
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    entity: Mapped[str] = mapped_column(String(100), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
