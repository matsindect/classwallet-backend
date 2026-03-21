"""Pydantic schemas for the audit module.

Defines response models for audit log API endpoints.  All schemas
inherit from CamelModel so field names are serialised as camelCase.
"""

import json
from datetime import datetime

from app.core.schemas import CamelModel


class AuditActorSummary(CamelModel):
    """Abbreviated actor (user) info embedded in an audit log entry."""

    id: str
    name: str
    email: str


class AuditLogResponse(CamelModel):
    """Response schema for an audit log entry.

    Attributes:
        id: Unique identifier for the log entry.
        actor: Summary of the user who performed the action.
        action: The action that was performed.
        entity: The entity type affected.
        entity_id: Identifier of the specific entity, if applicable.
        details: Parsed metadata dict (from metadata_json).
        ip_address: Client IP address.
        user_agent: Client User-Agent string.
        timestamp: When the action occurred.
    """

    id: str
    actor: AuditActorSummary | None = None
    action: str
    entity: str
    entity_id: str | None = None
    details: dict | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    timestamp: datetime

    @classmethod
    def from_model(cls, log) -> "AuditLogResponse":
        """Build an AuditLogResponse from an AuditLog ORM instance.

        Constructs the actor summary from the loaded User relationship
        and parses the metadata_json string into a dict.
        """
        actor = None
        if log.actor is not None:
            actor = AuditActorSummary(
                id=log.actor.id,
                name=f"{log.actor.first_name} {log.actor.last_name}",
                email=log.actor.email,
            )

        details = None
        if log.metadata_json:
            try:
                details = json.loads(log.metadata_json)
            except (json.JSONDecodeError, TypeError):
                details = None

        return cls(
            id=log.id,
            actor=actor,
            action=log.action,
            entity=log.entity,
            entity_id=log.entity_id,
            details=details,
            ip_address=log.ip_address,
            user_agent=log.user_agent,
            timestamp=log.timestamp,
        )
