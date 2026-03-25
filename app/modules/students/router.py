"""FastAPI router for student endpoints.

Exposes endpoints for listing students (with search, grade, and status
filters), creating and updating individual students, bulk CSV import,
and retrieving import history.  All endpoints require authentication and
role-based authorisation.

All responses use the uniform ``ApiResponse`` envelope via the helpers in
``app.core.response``.
"""

from fastapi import APIRouter, Depends, File, Query, UploadFile

from app.core.di import get_student_service
from app.core.pagination import clamp_pagination
from app.core.policy import enforce
from app.core.response import paginated_response, success_response
from app.modules.auth.dependencies import require_school_user
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
    current_user: UserResponse = Depends(require_school_user),
    service: StudentService = Depends(get_student_service),
    search: str | None = None,
    grade: str | None = None,
    status: str | None = None,
    page: int | None = Query(None),
    pageSize: int | None = Query(None),  # noqa: N803
):
    """List students with optional search, grade, and status filters.

    Returns a paginated response wrapped in the uniform API envelope.
    Requires the ``students.read`` permission.
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
    data = [StudentResponse.model_validate(s).model_dump(by_alias=True) for s in items]
    return paginated_response(data=data, page=p, page_size=ps, total_count=total)


@router.post("", status_code=201)
async def create_student(
    body: StudentCreate,
    current_user: UserResponse = Depends(require_school_user),
    service: StudentService = Depends(get_student_service),
):
    """Create a new student record.

    Requires the ``students.create`` permission. The student is associated
    with the authenticated user's school.
    """
    enforce(current_user, "students.create")
    student = await service.create_student(
        school_id=current_user.school_id,
        data=body,
        actor_id=current_user.id,
    )
    return success_response(
        data=StudentResponse.model_validate(student).model_dump(by_alias=True),
    )


@router.patch("/{student_id}")
async def update_student(
    student_id: str,
    body: StudentUpdate,
    current_user: UserResponse = Depends(require_school_user),
    service: StudentService = Depends(get_student_service),
):
    """Partially update an existing student.

    Requires the ``students.update`` permission.
    """
    enforce(current_user, "students.update")
    student = await service.update_student(
        student_id=student_id,
        data=body,
        actor_id=current_user.id,
        school_id=current_user.school_id,
    )
    return success_response(
        data=StudentResponse.model_validate(student).model_dump(by_alias=True),
    )


@router.post("/import")
async def import_students(
    file: UploadFile = File(...),
    current_user: UserResponse = Depends(require_school_user),
    service: StudentService = Depends(get_student_service),
):
    """Bulk-import students from an uploaded CSV file.

    Requires the ``students.import`` permission.
    """
    enforce(current_user, "students.import")
    content = await file.read()
    imp = await service.import_students(
        school_id=current_user.school_id,
        file_content=content,
        file_name=file.filename or "import.csv",
        actor_id=current_user.id,
    )
    return success_response(
        data=StudentImportResponse.from_import(imp).model_dump(by_alias=True),
    )


@router.get("/imports")
async def list_imports(
    current_user: UserResponse = Depends(require_school_user),
    service: StudentService = Depends(get_student_service),
):
    """List all past CSV import operations for the current school.

    Requires the ``students.read`` permission.
    """
    enforce(current_user, "students.read")
    imports = await service.list_imports(current_user.school_id)
    data = [StudentImportResponse.from_import(i).model_dump(by_alias=True) for i in imports]
    return success_response(data=data)
