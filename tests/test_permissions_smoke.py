"""Smoke tests for role-based access control (RBAC) enforcement.

Verifies that a STAFF-role user is denied access to admin-only
endpoints (user management, fee structures, audit logs) while retaining
read access to student data.  Also confirms that an ADMIN user can
access the audit logs endpoint.
"""

import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.core.security import hash_password
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission
from tests.conftest import SCHOOL_ID, TestSessionLocal, app

# STAFF permissions: limited student and payment access
_STAFF_PERMISSIONS = [
    "payments.read",
    "students.create",
    "students.read",
    "students.update",
    "students.import",
]


@pytest_asyncio.fixture
async def staff_token(seed_data):
    """Create a STAFF role and user, then return their auth token."""
    staff_id = str(uuid.uuid4())
    staff_role_id = str(uuid.uuid4())
    async with TestSessionLocal() as session:
        # Create STAFF role
        staff_role = Role(
            id=staff_role_id,
            name="STAFF",
            slug="staff",
            is_system=True,
        )
        session.add(staff_role)
        await session.flush()

        # Assign subset of permissions
        for action in _STAFF_PERMISSIONS:
            result = await session.execute(select(Permission).where(Permission.action == action))
            perm = result.scalar_one()
            session.add(RolePermission(role_id=staff_role_id, permission_id=perm.id))

        user = User(
            id=staff_id,
            school_id=SCHOOL_ID,
            email="staff@test.com",
            first_name="Staff",
            last_name="User",
            password_hash=hash_password("password123"),
            role_id=staff_role_id,
        )
        session.add(user)
        await session.commit()

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/auth/login",
            json={"email": "staff@test.com", "password": "password123"},
        )
        return resp.json()["data"]["token"]


@pytest.mark.asyncio
async def test_staff_cannot_manage_users(client: AsyncClient, staff_token):
    """Verify that STAFF users receive 403 when listing school users."""
    headers = {"Authorization": f"Bearer {staff_token}"}
    resp = await client.get("/school/users", headers=headers)
    assert resp.status_code == 403
    assert resp.json()["error"]["code"] == "FORBIDDEN"


@pytest.mark.asyncio
async def test_staff_cannot_manage_fees(client: AsyncClient, staff_token):
    """Verify that STAFF users receive 403 when accessing fee structures."""
    headers = {"Authorization": f"Bearer {staff_token}"}
    resp = await client.get("/fees/structures", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_staff_can_view_students(client: AsyncClient, staff_token):
    """Verify that STAFF users are allowed to view the student list."""
    headers = {"Authorization": f"Bearer {staff_token}"}
    resp = await client.get("/students", headers=headers)
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_staff_cannot_view_audit(client: AsyncClient, staff_token):
    """Verify that STAFF users receive 403 when accessing audit logs."""
    headers = {"Authorization": f"Bearer {staff_token}"}
    resp = await client.get("/audit/logs", headers=headers)
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_view_audit(client: AsyncClient, auth_headers):
    """Verify that ADMIN users can successfully access audit logs."""
    resp = await client.get("/audit/logs", headers=auth_headers)
    assert resp.status_code == 200
