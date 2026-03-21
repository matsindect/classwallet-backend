"""Tests for the students module.

Covers student creation, paginated listing, partial updates, CSV bulk
import, and listing previous import operations.  All responses use the
uniform envelope: ``{success, data, error, meta}``.
"""

import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_student(client: AsyncClient, auth_headers):
    """Verify that a new student can be created and the response contains the correct fields."""
    resp = await client.post(
        "/students",
        json={"firstName": "Jane", "lastName": "Doe", "grade": "Grade 10"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["firstName"] == "Jane"
    assert body["data"]["lastName"] == "Doe"


@pytest.mark.asyncio
async def test_list_students_paginated(client: AsyncClient, auth_headers):
    """Verify that the student list endpoint returns paginated results with metadata."""
    # Create a few students
    for i in range(3):
        await client.post(
            "/students",
            json={"firstName": f"Student{i}", "lastName": "Test", "grade": "Grade 10"},
            headers=auth_headers,
        )

    resp = await client.get("/students?page=1&pageSize=2", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert "data" in body
    assert "meta" in body
    assert body["meta"]["pageSize"] == 2
    assert body["meta"]["totalCount"] >= 3


@pytest.mark.asyncio
async def test_update_student(client: AsyncClient, auth_headers):
    """Verify that a student's fields can be partially updated via PATCH."""
    resp = await client.post(
        "/students",
        json={"firstName": "Update", "lastName": "Me", "grade": "Grade 10"},
        headers=auth_headers,
    )
    student_id = resp.json()["data"]["id"]

    resp = await client.patch(
        f"/students/{student_id}",
        json={"grade": "Grade 12"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["grade"] == "Grade 12"


@pytest.mark.asyncio
async def test_import_students(client: AsyncClient, auth_headers):
    """Verify that students can be bulk-imported from a CSV file."""
    csv_content = "first_name,last_name,grade,email\nImported,Student,Grade 9,imported@test.com\n"
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    resp = await client.post("/students/import", files=files, headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert body["data"]["totalRows"] == 1
    assert body["data"]["successRows"] == 1


@pytest.mark.asyncio
async def test_list_imports(client: AsyncClient, auth_headers):
    """Verify that the imports listing endpoint returns a list."""
    resp = await client.get("/students/imports", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)
