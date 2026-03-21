"""Business-logic layer for student management.

Orchestrates student CRUD, paginated listing with filters, CSV bulk
import, and import history retrieval. All mutations are logged to the
audit system.
"""

import csv
import io
import json
from datetime import UTC, datetime

from app.core.errors import NotFoundError, ValidationError
from app.modules.audit.repository import AuditRepository
from app.modules.students.models import Guardian, Student, StudentImport
from app.modules.students.repository import StudentRepository
from app.modules.students.schemas import StudentCreate, StudentUpdate


class StudentService:
    """Service encapsulating student business logic.

    Args:
        repo: The student data-access repository.
        audit_repo: The audit-log repository used to record mutations.
    """

    def __init__(self, repo: StudentRepository, audit_repo: AuditRepository):
        self.repo = repo
        self.audit_repo = audit_repo

    async def list_students(
        self,
        school_id: str,
        page: int,
        page_size: int,
        search: str | None = None,
        grade: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Student], int]:
        """Return a paginated, optionally filtered list of students.

        Converts page-based parameters to offset/limit before delegating
        to the repository.
        """
        offset = (page - 1) * page_size
        return await self.repo.list_students(
            school_id=school_id,
            offset=offset,
            limit=page_size,
            search=search,
            grade=grade,
            status=status,
        )

    async def create_student(self, school_id: str, data: StudentCreate, actor_id: str) -> Student:
        """Create a new student (with optional guardians) and log the action.

        Generates a ``student_id`` display identifier and sets ``enrollment_date``
        to today if not provided.
        """
        # Build the student model from the schema, excluding guardians
        student_fields = data.model_dump(exclude={"guardians"}, exclude_unset=True)
        student = Student(school_id=school_id, **student_fields)

        # Generate a display student_id
        student.student_id = await self._generate_student_id(school_id)

        # Default enrollment_date to today
        if not student.enrollment_date:
            student.enrollment_date = datetime.now(UTC).strftime("%Y-%m-%d")

        # Create guardian objects if provided
        if data.guardians:
            for g in data.guardians:
                guardian = Guardian(
                    first_name=g.first_name,
                    last_name=g.last_name,
                    relationship=g.relationship,
                    phone=g.phone,
                    email=g.email,
                    is_primary=g.is_primary,
                )
                student.guardians.append(guardian)

        student = await self.repo.create_student(student)
        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="student",
            entity_id=student.id,
        )
        return student

    async def update_student(
        self, student_id: str, data: StudentUpdate, actor_id: str, school_id: str
    ) -> Student:
        """Partially update a student record and log the action.

        When ``guardians`` is provided in the update payload, all existing
        guardians are replaced with the new set (full replacement).
        """
        guardians_data = data.guardians
        update_fields = data.model_dump(exclude={"guardians"}, exclude_unset=True)

        student = await self.repo.update_student(student_id, update_fields)
        if not student:
            raise NotFoundError(message="Student not found")

        # Replace guardians if provided
        if guardians_data is not None:
            await self.repo.replace_guardians(student, guardians_data)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="student",
            entity_id=student_id,
        )
        return student

    async def import_students(
        self, school_id: str, file_content: bytes, file_name: str, actor_id: str
    ) -> StudentImport:
        """Bulk-import students from a CSV file.

        Parses the CSV content and creates one ``Student`` record per valid
        row. Expected CSV headers: ``first_name``, ``last_name``, ``grade``,
        ``email``, ``phone``, ``guardian_name``, ``guardian_email``,
        ``guardian_phone``.  Rows missing ``first_name`` or ``last_name``
        are skipped and recorded as failures.
        """
        text = file_content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))

        total = 0
        success = 0
        failed = 0
        errors_list: list[dict] = []

        for row_num, row in enumerate(reader, start=2):
            total += 1
            first_name = row.get("first_name", "").strip()
            last_name = row.get("last_name", "").strip()
            if not first_name or not last_name:
                failed += 1
                errors_list.append({"row": row_num, "error": "Missing first_name or last_name"})
                continue

            student = Student(
                school_id=school_id,
                first_name=first_name,
                last_name=last_name,
                email=row.get("email", "").strip() or None,
                phone=row.get("phone", "").strip() or None,
                grade=row.get("grade", "").strip() or None,
                class_name=row.get("class_name", "").strip() or None,
                date_of_birth=row.get("date_of_birth", "").strip() or None,
                guardian_name=row.get("guardian_name", "").strip() or None,
                guardian_email=row.get("guardian_email", "").strip() or None,
                guardian_phone=row.get("guardian_phone", "").strip() or None,
                enrollment_date=datetime.now(UTC).strftime("%Y-%m-%d"),
            )
            # Generate a display student_id for each imported student
            student.student_id = await self._generate_student_id(school_id)

            try:
                await self.repo.create_student(student)
                success += 1
            except Exception:
                failed += 1
                errors_list.append({"row": row_num, "error": "Database error"})

        if total == 0:
            raise ValidationError(message="CSV file is empty or has no valid rows")

        imp = StudentImport(
            school_id=school_id,
            file_name=file_name,
            total_rows=total,
            successful_rows=success,
            failed_rows=failed,
            status="completed",
            errors=json.dumps(errors_list) if errors_list else None,
            created_by=actor_id,
        )
        imp = await self.repo.create_import(imp)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="import",
            entity="student_import",
            entity_id=imp.id,
            metadata={"total": total, "success": success, "failed": failed},
        )
        return imp

    async def list_imports(self, school_id: str) -> list[StudentImport]:
        """Return all import history records for a school."""
        return await self.repo.list_imports(school_id)

    async def _generate_student_id(self, school_id: str) -> str:
        """Generate a sequential display student ID.

        Format: ``STD-YYYY-NNN`` where NNN is zero-padded based on the
        current count of students in the school.
        """
        count = await self.repo.count_students(school_id)
        year = datetime.now(UTC).strftime("%Y")
        return f"STD-{year}-{count + 1:03d}"
