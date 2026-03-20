"""Data-access layer for student and student-import records.

Provides async CRUD operations and filtered/paginated queries against the
``students`` and ``student_imports`` tables via SQLAlchemy.
"""

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.models import Student, StudentImport


class StudentRepository:
    """Repository encapsulating all database operations for students.

    Args:
        session: An async SQLAlchemy session used for all queries.
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_students(
        self,
        school_id: str,
        offset: int = 0,
        limit: int = 20,
        search: str | None = None,
        grade: str | None = None,
        status: str | None = None,
    ) -> tuple[list[Student], int]:
        """Return a paginated, optionally filtered list of students.

        Args:
            school_id: Scope results to this school.
            offset: Number of rows to skip (for pagination).
            limit: Maximum number of rows to return.
            search: Optional case-insensitive substring match against
                first_name or last_name.
            grade: Optional exact-match filter on grade.
            status: Optional exact-match filter on enrolment status.

        Returns:
            A tuple of (list of matching ``Student`` objects, total count).
        """
        q = select(Student).where(Student.school_id == school_id)
        count_q = select(func.count(Student.id)).where(Student.school_id == school_id)

        if search:
            pattern = f"%{search}%"
            filter_expr = (Student.first_name.ilike(pattern)) | (
                Student.last_name.ilike(pattern)
            )
            q = q.where(filter_expr)
            count_q = count_q.where(filter_expr)
        if grade:
            q = q.where(Student.grade == grade)
            count_q = count_q.where(Student.grade == grade)
        if status:
            q = q.where(Student.status == status)
            count_q = count_q.where(Student.status == status)

        total = (await self.session.execute(count_q)).scalar() or 0
        result = await self.session.execute(
            q.order_by(Student.created_at.desc()).offset(offset).limit(limit)
        )
        return list(result.scalars().all()), total

    async def create_student(self, student: Student) -> Student:
        """Persist a new student record.

        Args:
            student: A ``Student`` instance to insert.

        Returns:
            The same ``Student`` instance after flushing to the database.
        """
        self.session.add(student)
        await self.session.flush()
        return student

    async def get_by_id(self, student_id: str) -> Student | None:
        """Fetch a single student by primary key.

        Args:
            student_id: The UUID of the student.

        Returns:
            The ``Student`` if found, otherwise ``None``.
        """
        result = await self.session.execute(select(Student).where(Student.id == student_id))
        return result.scalar_one_or_none()

    async def update_student(self, student_id: str, data: dict) -> Student | None:
        """Apply a partial update to an existing student.

        Only keys present in *data* whose values are not ``None`` are written.

        Args:
            student_id: The UUID of the student to update.
            data: Dictionary of field names to new values.

        Returns:
            The updated ``Student``, or ``None`` if no student was found.
        """
        result = await self.session.execute(select(Student).where(Student.id == student_id))
        student = result.scalar_one_or_none()
        if not student:
            return None
        for key, value in data.items():
            if hasattr(student, key) and value is not None:
                setattr(student, key, value)
        await self.session.flush()
        return student

    async def get_students_by_grade(self, school_id: str, grade: str) -> list[Student]:
        """Return all students in a given school and grade.

        Args:
            school_id: The school to scope results to.
            grade: The grade/class level to filter by.

        Returns:
            A list of matching ``Student`` objects.
        """
        result = await self.session.execute(
            select(Student).where(Student.school_id == school_id, Student.grade == grade)
        )
        return list(result.scalars().all())

    async def get_all_students(self, school_id: str) -> list[Student]:
        """Return every student belonging to a school.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of all ``Student`` objects for the school.
        """
        result = await self.session.execute(
            select(Student).where(Student.school_id == school_id)
        )
        return list(result.scalars().all())

    async def create_import(self, imp: StudentImport) -> StudentImport:
        """Persist a student-import result record.

        Args:
            imp: A ``StudentImport`` instance to insert.

        Returns:
            The same ``StudentImport`` instance after flushing.
        """
        self.session.add(imp)
        await self.session.flush()
        return imp

    async def list_imports(self, school_id: str) -> list[StudentImport]:
        """Return all import records for a school, newest first.

        Args:
            school_id: The school to scope results to.

        Returns:
            A list of ``StudentImport`` objects ordered by descending
            ``created_at``.
        """
        result = await self.session.execute(
            select(StudentImport)
            .where(StudentImport.school_id == school_id)
            .order_by(StudentImport.created_at.desc())
        )
        return list(result.scalars().all())
