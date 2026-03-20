"""Tests for the students module.

Covers student creation, paginated listing, partial updates, CSV bulk
import, and listing previous import operations.
"""

import io

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_create_student(client: AsyncClient, auth_headers):
    """Verify that a new student can be created and the response contains the correct fields."""
    resp = await client.post(
        "/students",
        json={"first_name": "Jane", "last_name": "Doe", "grade": "Grade 10"},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["first_name"] == "Jane"
    assert data["last_name"] == "Doe"


@pytest.mark.asyncio
async def test_list_students_paginated(client: AsyncClient, auth_headers):
    """Verify that the student list endpoint returns paginated results with metadata."""
    # Create a few students
    for i in range(3):
        await client.post(
            "/students",
            json={"first_name": f"Student{i}", "last_name": "Test"},
            headers=auth_headers,
        )

    resp = await client.get("/students?page=1&pageSize=2", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "meta" in data
    assert data["meta"]["pageSize"] == 2
    assert data["meta"]["totalCount"] >= 3


@pytest.mark.asyncio
async def test_update_student(client: AsyncClient, auth_headers):
    """Verify that a student's fields can be partially updated via PATCH."""
    resp = await client.post(
        "/students",
        json={"first_name": "Update", "last_name": "Me"},
        headers=auth_headers,
    )
    student_id = resp.json()["id"]

    resp = await client.patch(
        f"/students/{student_id}",
        json={"grade": "Grade 12"},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["grade"] == "Grade 12"


@pytest.mark.asyncio
async def test_import_students(client: AsyncClient, auth_headers):
    """Verify that students can be bulk-imported from a CSV file."""
    csv_content = "first_name,last_name,grade,email\nImported,Student,Grade 9,imported@test.com\n"
    files = {"file": ("students.csv", io.BytesIO(csv_content.encode()), "text/csv")}

    resp = await client.post("/students/import", files=files, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_rows"] == 1
    assert data["successful_rows"] == 1


@pytest.mark.asyncio
async def test_list_imports(client: AsyncClient, auth_headers):
    """Verify that the imports listing endpoint returns a list."""
    resp = await client.get("/students/imports", headers=auth_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
