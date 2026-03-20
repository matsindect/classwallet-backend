"""Shared pytest fixtures for the Class Wallet test suite.

Sets up an in-memory (file-based SQLite) async test database, overrides
the ``get_db_session`` dependency so the FastAPI app uses the test engine,
and provides reusable fixtures for database seeding, an ``AsyncClient``,
and pre-authenticated admin headers.
"""

import asyncio
import uuid
from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.database import Base, get_db_session
from app.core.security import hash_password
from app.main import app
from app.modules.auth.models import User
from app.modules.school.models import School

TEST_DB_URL = "sqlite+aiosqlite:///./test_class_wallet.db"

engine = create_async_engine(TEST_DB_URL, echo=False)
TestSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


@pytest.fixture(scope="session")
def event_loop():
    """Provide a session-scoped event loop for async tests.

    Yields:
        asyncio.AbstractEventLoop: A new event loop shared across the
        entire test session.
    """
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test and drop them afterwards.

    This fixture runs automatically for every test to ensure a clean
    database state.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency override that yields a test database session.

    Commits on success and rolls back on any exception so that each
    request gets a clean transactional boundary.

    Yields:
        AsyncSession: An async SQLAlchemy session bound to the test engine.
    """
    async with TestSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


app.dependency_overrides[get_db_session] = override_get_db

SCHOOL_ID = str(uuid.uuid4())
ADMIN_ID = str(uuid.uuid4())


@pytest_asyncio.fixture
async def seed_data():
    """Insert a test school and an ADMIN user into the test database.

    The school and admin IDs are module-level constants (``SCHOOL_ID``,
    ``ADMIN_ID``) so that other fixtures can reference them.
    """
    async with TestSessionLocal() as session:
        school = School(id=SCHOOL_ID, name="Test School")
        session.add(school)
        admin = User(
            id=ADMIN_ID,
            school_id=SCHOOL_ID,
            email="admin@test.com",
            first_name="Admin",
            last_name="User",
            password_hash=hash_password("password123"),
            role="ADMIN",
        )
        session.add(admin)
        await session.commit()


@pytest_asyncio.fixture
async def client():
    """Provide an async HTTP client wired to the FastAPI test app.

    Yields:
        AsyncClient: An httpx ``AsyncClient`` that sends requests
        directly to the ASGI application without network I/O.
    """
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_token(client: AsyncClient, seed_data) -> str:
    """Log in as the seeded ADMIN user and return a JWT token.

    Args:
        client: The async HTTP test client.
        seed_data: Ensures the test school and admin user exist.

    Returns:
        str: A valid bearer token for the admin user.
    """
    resp = await client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    return resp.json()["token"]


@pytest_asyncio.fixture
def auth_headers(auth_token: str) -> dict[str, str]:
    """Build an Authorization header dict from the admin token.

    Args:
        auth_token: A valid JWT bearer token.

    Returns:
        dict[str, str]: Headers dict suitable for passing to httpx requests.
    """
    return {"Authorization": f"Bearer {auth_token}"}
