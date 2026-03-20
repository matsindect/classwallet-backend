"""Business-logic layer for student management.

Orchestrates student CRUD, paginated listing with filters, CSV bulk
import, and import history retrieval. All mutations are logged to the
audit system.
"""

import csv
import io
import json

from app.core.errors import NotFoundError, ValidationError
from app.modules.audit.repository import AuditRepository
from app.modules.students.models import Student, StudentImport
from app.modules.students.repository import StudentRepository


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

        Args:
            school_id: Scope results to this school.
            page: 1-based page number.
            page_size: Number of records per page.
            search: Optional substring search on student names.
            grade: Optional exact-match grade filter.
            status: Optional exact-match status filter.

        Returns:
            A tuple of (list of ``Student`` objects, total matching count).
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

    async def create_student(self, school_id: str, data: dict, actor_id: str) -> Student:
        """Create a new student and log the action to the audit trail.

        Args:
            school_id: The school the student belongs to.
            data: Dictionary of student field values.
            actor_id: ID of the user performing the action.

        Returns:
            The newly created ``Student`` instance.
        """
        student = Student(school_id=school_id, **data)
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
        self, student_id: str, data: dict, actor_id: str, school_id: str
    ) -> Student:
        """Partially update a student record and log the action.

        Args:
            student_id: UUID of the student to update.
            data: Dictionary of fields to update.
            actor_id: ID of the user performing the action.
            school_id: School context for audit logging.

        Returns:
            The updated ``Student`` instance.

        Raises:
            NotFoundError: If no student matches *student_id*.
        """
        student = await self.repo.update_student(student_id, data)
        if not student:
            raise NotFoundError(message="Student not found")
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

        Args:
            school_id: The school to import students into.
            file_content: Raw bytes of the uploaded CSV file (UTF-8 or
                UTF-8-BOM encoded).
            file_name: Original file name for record-keeping.
            actor_id: ID of the user who initiated the import.

        Returns:
            A ``StudentImport`` record summarising the import outcome.

        Raises:
            ValidationError: If the CSV is empty or contains no data rows.
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
                guardian_name=row.get("guardian_name", "").strip() or None,
                guardian_email=row.get("guardian_email", "").strip() or None,
                guardian_phone=row.get("guardian_phone", "").strip() or None,
            )
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
        """Return all import history records for a school.

        Args:
            school_id: The school whose import history to retrieve.

        Returns:
            A list of ``StudentImport`` records, newest first.
        """
        return await self.repo.list_imports(school_id)
