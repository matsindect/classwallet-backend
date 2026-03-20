"""Pydantic schemas for the audit module.

Defines response models for audit log API endpoints.
"""

from datetime import datetime

from pydantic import BaseModel


class AuditLogResponse(BaseModel):
    """Response schema for an audit log entry.

    Serializes an AuditLog ORM model for API responses. Configured with
    ``from_attributes`` to support direct construction from SQLAlchemy
    model instances.

    Attributes:
        id: Unique identifier for the log entry.
        school_id: Identifier of the school this entry belongs to.
        actor_id: Identifier of the actor who performed the action.
        action: The action that was performed.
        entity: The entity type affected.
        entity_id: Identifier of the specific entity, if applicable.
        metadata_json: Optional JSON string with additional context.
        timestamp: When the action occurred.
    """

    id: str
    school_id: str
    actor_id: str
    action: str
    entity: str
    entity_id: str | None = None
    metadata_json: str | None = None
    timestamp: datetime

    model_config = {"from_attributes": True}
