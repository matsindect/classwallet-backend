"""Tests for the authentication module.

Covers successful and failed login, the ``/auth/me`` endpoint (with and
without a token), logout, and verification that a token is invalidated
after logout.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, seed_data):
    """Verify that valid credentials return a 200 with a token and user info."""
    resp = await client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "token" in data
    assert data["user"]["email"] == "admin@test.com"
    assert data["user"]["role"] == "ADMIN"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, seed_data):
    """Verify that an incorrect password returns 401 with AUTH_ERROR code."""
    resp = await client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "wrong"},
    )
    assert resp.status_code == 401
    data = resp.json()
    assert data["code"] == "AUTH_ERROR"


@pytest.mark.asyncio
async def test_me(client: AsyncClient, auth_headers):
    """Verify that ``/auth/me`` returns the authenticated user's profile."""
    resp = await client.get("/auth/me", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["email"] == "admin@test.com"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient, seed_data):
    """Verify that ``/auth/me`` without a token returns 401 or 403."""
    resp = await client.get("/auth/me")
    assert resp.status_code in (401, 403)


@pytest.mark.asyncio
async def test_logout(client: AsyncClient, auth_headers):
    """Verify that logout returns 204 No Content."""
    resp = await client.post("/auth/logout", headers=auth_headers)
    assert resp.status_code == 204


@pytest.mark.asyncio
async def test_token_invalidated_after_logout(client: AsyncClient, seed_data):
    """Verify that a token is rejected after the user has logged out."""
    # Login
    resp = await client.post(
        "/auth/login",
        json={"email": "admin@test.com", "password": "password123"},
    )
    token = resp.json()["token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Logout
    resp = await client.post("/auth/logout", headers=headers)
    assert resp.status_code == 204

    # Token should now be invalid (token version incremented)
    resp = await client.get("/auth/me", headers=headers)
    assert resp.status_code == 401
