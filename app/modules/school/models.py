"""School entity model.

Defines the SQLAlchemy ORM model for schools, which serve as the
top-level organizational unit in the application.  Each school has its
own set of users, currency, and timezone settings.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class School(Base):
    """Represents a school organization in the system.

    A school is the primary tenant boundary.  Users, financial
    transactions, and other domain objects are scoped to a school.

    Attributes:
        id: UUID primary key.
        name: Display name of the school.
        address: Optional physical address.
        phone: Optional contact phone number.
        email: Optional contact email address.
        website: Optional website URL.
        logo_url: Optional URL to the school's logo image.
        currency: ISO 4217 currency code (default ``USD``).
        timezone: IANA timezone identifier (default ``UTC``).
        created_at: Timestamp of creation (UTC).
        updated_at: Timestamp of last modification (UTC).
    """
    __tablename__ = "schools"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    phone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    website: Mapped[str | None] = mapped_column(String(255), nullable=True)
    logo_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    currency: Mapped[str] = mapped_column(String(10), default="USD")
    timezone: Mapped[str] = mapped_column(String(50), default="UTC")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
