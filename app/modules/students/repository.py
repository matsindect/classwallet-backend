"""Data-access layer for student and student-import records.

Provides async CRUD operations and filtered/paginated queries against the
``students``, ``guardians``, and ``student_imports`` tables via SQLAlchemy.
"""

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.students.models import Guardian, Student, StudentImport


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

        The search filter matches against first_name, last_name, or the
        display student_id.
        """
        q = select(Student).where(Student.school_id == school_id)
        count_q = select(func.count(Student.id)).where(Student.school_id == school_id)

        if search:
            pattern = f"%{search}%"
            filter_expr = (
                Student.first_name.ilike(pattern)
                | Student.last_name.ilike(pattern)
                | Student.student_id.ilike(pattern)
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
        """Persist a new student record (with any appended guardians)."""
        self.session.add(student)
        await self.session.flush()
        await self.session.refresh(student, attribute_names=["guardians"])
        return student

    async def get_by_id(self, student_id: str) -> Student | None:
        """Fetch a single student by primary key."""
        from sqlalchemy.orm import selectinload

        result = await self.session.execute(
            select(Student).where(Student.id == student_id).options(selectinload(Student.guardians))
        )
        return result.scalar_one_or_none()

    async def update_student(self, student_id: str, data: dict) -> Student | None:
        """Apply a partial update to an existing student.

        Only keys present in *data* whose values are not ``None`` are written.
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

    async def replace_guardians(self, student: Student, guardians_data: list) -> None:
        """Replace all guardians for a student with a new set.

        Deletes existing guardians and inserts the new ones.
        """
        await self.session.execute(delete(Guardian).where(Guardian.student_id == student.id))
        # Clear the in-memory collection so SQLAlchemy doesn't conflict
        student.guardians.clear()

        for g in guardians_data:
            guardian = Guardian(
                student_id=student.id,
                first_name=g.first_name,
                last_name=g.last_name,
                relationship=g.relationship,
                phone=g.phone,
                email=g.email,
                is_primary=g.is_primary,
            )
            student.guardians.append(guardian)
            self.session.add(guardian)

        await self.session.flush()

    async def count_students(self, school_id: str) -> int:
        """Return the total number of students in a school."""
        result = await self.session.execute(
            select(func.count(Student.id)).where(Student.school_id == school_id)
        )
        return result.scalar() or 0

    async def get_students_by_grade(self, school_id: str, grade: str) -> list[Student]:
        """Return all students in a given school and grade."""
        result = await self.session.execute(
            select(Student).where(Student.school_id == school_id, Student.grade == grade)
        )
        return list(result.scalars().all())

    async def get_students_by_grades(self, school_id: str, grades: list[str]) -> list[Student]:
        """Return all students in a given school matching any of the provided grades.

        Args:
            school_id: The school to scope results to.
            grades: List of grade/class levels to filter by.

        Returns:
            A list of matching ``Student`` objects.
        """
        result = await self.session.execute(
            select(Student).where(Student.school_id == school_id, Student.grade.in_(grades))
        )
        return list(result.scalars().all())

    async def get_all_students(self, school_id: str) -> list[Student]:
        """Return every student belonging to a school."""
        result = await self.session.execute(select(Student).where(Student.school_id == school_id))
        return list(result.scalars().all())

    async def create_import(self, imp: StudentImport) -> StudentImport:
        """Persist a student-import result record."""
        self.session.add(imp)
        await self.session.flush()
        return imp

    async def list_imports(self, school_id: str) -> list[StudentImport]:
        """Return all import records for a school, newest first."""
        result = await self.session.execute(
            select(StudentImport)
            .where(StudentImport.school_id == school_id)
            .order_by(StudentImport.created_at.desc())
        )
        return list(result.scalars().all())
