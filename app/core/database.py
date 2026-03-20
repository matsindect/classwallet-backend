"""Async SQLAlchemy database engine, session factory, and base model.

Provides the core database infrastructure used by the entire application:

* An async engine connected to the URL specified in ``settings.DATABASE_URL``.
* A session factory (``async_session_factory``) that produces
  ``AsyncSession`` instances.
* A declarative ``Base`` class that all ORM models inherit from.
* A ``get_db_session`` async generator suitable for use as a FastAPI
  dependency, handling commit/rollback semantics automatically.
"""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True,
)

async_session_factory = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Declarative base for all SQLAlchemy ORM models in the application."""

    pass


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Provide a transactional async database session as a FastAPI dependency.

    Yields an ``AsyncSession`` that is automatically committed when the
    request handler returns successfully.  If any exception propagates, the
    session is rolled back before the exception is re-raised.

    Yields:
        AsyncSession: An active async SQLAlchemy session.

    Raises:
        Exception: Re-raises any exception after rolling back the session.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
