"""FastAPI router for student endpoints.

Exposes endpoints for listing students (with search, grade, and status
filters), creating and updating individual students, bulk CSV import,
and retrieving import history.  All endpoints require authentication and
role-based authorisation.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.di import get_student_service
from app.core.pagination import clamp_pagination, paginate
from app.core.policy import enforce
from app.modules.auth.dependencies import get_current_user
from app.modules.auth.schemas import UserResponse
from app.modules.students.schemas import (
    StudentCreate,
    StudentImportResponse,
    StudentResponse,
    StudentUpdate,
)
from app.modules.students.service import StudentService

router = APIRouter(prefix="/students", tags=["Students"])


@router.get("")
async def list_students(
    current_user: UserResponse = Depends(get_current_user),
    service: StudentService = Depends(get_student_service),
    search: str | None = None,
    grade: str | None = None,
    status: str | None = None,
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List students with optional search, grade, and status filters.

    Returns a paginated response. Requires the ``view_students`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: StudentService instance (injected).
        search: Optional substring match on first/last name.
        grade: Optional exact grade filter.
        status: Optional exact status filter.
        page: 1-based page number.
        pageSize: Number of records per page.

    Returns:
        A paginated dict containing student data and pagination metadata.
    """
    enforce(current_user, "students.read")
    p, ps = clamp_pagination(page, pageSize)
    items, total = await service.list_students(
        school_id=current_user.school_id,
        page=p,
        page_size=ps,
        search=search,
        grade=grade,
        status=status,
    )
    data = [StudentResponse.model_validate(s) for s in items]
    return paginate(data, total, p, ps)


@router.post("", response_model=StudentResponse, status_code=201)
async def create_student(
    body: StudentCreate,
    current_user: UserResponse = Depends(get_current_user),
    service: StudentService = Depends(get_student_service),
):
    """Create a new student record.

    Requires the ``manage_students`` permission. The student is associated
    with the authenticated user's school.

    Args:
        body: Student creation payload.
        current_user: The authenticated user (injected).
        service: StudentService instance (injected).

    Returns:
        The created student as a ``StudentResponse``.
    """
    enforce(current_user, "students.create")
    student = await service.create_student(
        school_id=current_user.school_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
    )
    return StudentResponse.model_validate(student)


@router.patch("/{student_id}", response_model=StudentResponse)
async def update_student(
    student_id: str,
    body: StudentUpdate,
    current_user: UserResponse = Depends(get_current_user),
    service: StudentService = Depends(get_student_service),
):
    """Partially update an existing student.

    Requires the ``manage_students`` permission.

    Args:
        student_id: UUID of the student to update.
        body: Fields to update (only set fields are applied).
        current_user: The authenticated user (injected).
        service: StudentService instance (injected).

    Returns:
        The updated student as a ``StudentResponse``.

    Raises:
        NotFoundError: If the student does not exist.
    """
    enforce(current_user, "students.update")
    student = await service.update_student(
        student_id=student_id,
        data=body.model_dump(exclude_unset=True),
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return StudentResponse.model_validate(student)


@router.post("/import", response_model=StudentImportResponse)
async def import_students(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(get_current_user),
    service: StudentService = Depends(get_student_service),
):
    """Bulk-import students from an uploaded CSV file.

    Expects a multipart file upload with CSV headers: ``first_name``,
    ``last_name``, ``grade``, ``email``, ``phone``, ``guardian_name``,
    ``guardian_email``, ``guardian_phone``. Requires the
    ``manage_students`` permission.

    Args:
        file: The uploaded CSV file.
        current_user: The authenticated user (injected).
        service: StudentService instance (injected).

    Returns:
        A ``StudentImportResponse`` with row-level statistics.
    """
    enforce(current_user, "students.import")
    content = await file.read()
    imp = await service.import_students(
        school_id=current_user.school_id,
        file_content=content,
        file_name=file.filename or "import.csv",
        actor_id=current_user.id,
    )
    return StudentImportResponse.model_validate(imp)


@router.get("/imports", response_model=list[StudentImportResponse])
async def list_imports(
    current_user: UserResponse = Depends(get_current_user),
    service: StudentService = Depends(get_student_service),
):
    """List all past CSV import operations for the current school.

    Requires the ``manage_students`` permission.

    Args:
        current_user: The authenticated user (injected).
        service: StudentService instance (injected).

    Returns:
        A list of ``StudentImportResponse`` objects, newest first.
    """
    enforce(current_user, "students.read")
    imports = await service.list_imports(current_user.school_id)
    return [StudentImportResponse.model_validate(i) for i in imports]
