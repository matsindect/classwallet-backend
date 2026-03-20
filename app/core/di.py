"""Dependency injection providers using FastAPI ``Depends``.

Centralises the construction of every repository and service in the
application.  Each ``_get_*_repository`` function receives an
``AsyncSession`` via FastAPI's dependency injection and returns the
corresponding repository instance.  The public ``get_*_service`` functions
compose repositories into fully-wired service objects.

Routers import ``get_*_service`` functions and never touch the DB session
directly, keeping the transport layer decoupled from persistence.

Imports of concrete repository and service classes are performed lazily
inside each function body to avoid circular-import issues at module load
time.
"""

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session

# --- Repositories ---


def _get_audit_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide an ``AuditRepository`` instance bound to the current session."""
    from app.modules.audit.repository import AuditRepository

    return AuditRepository(session)


def _get_auth_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide an ``AuthRepository`` instance bound to the current session."""
    from app.modules.auth.repository import AuthRepository

    return AuthRepository(session)


def _get_school_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide a ``SchoolRepository`` instance bound to the current session."""
    from app.modules.school.repository import SchoolRepository

    return SchoolRepository(session)


def _get_student_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide a ``StudentRepository`` instance bound to the current session."""
    from app.modules.students.repository import StudentRepository

    return StudentRepository(session)


def _get_fee_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide a ``FeeRepository`` instance bound to the current session."""
    from app.modules.fees.repository import FeeRepository

    return FeeRepository(session)


def _get_payment_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide a ``PaymentRepository`` instance bound to the current session."""
    from app.modules.payments.repository import PaymentRepository

    return PaymentRepository(session)


def _get_reminder_repository(session: AsyncSession = Depends(get_db_session)):
    """Provide a ``ReminderRepository`` instance bound to the current session."""
    from app.modules.reminders.repository import ReminderRepository

    return ReminderRepository(session)


# --- Services ---


def get_audit_service(repo=Depends(_get_audit_repository)):
    """Provide an ``AuditService`` wired with its repository."""
    from app.modules.audit.service import AuditService

    return AuditService(repo)


def get_auth_service(
    repo=Depends(_get_auth_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide an ``AuthService`` wired with auth and audit repositories."""
    from app.modules.auth.service import AuthService

    return AuthService(repo, audit)


def get_school_service(
    repo=Depends(_get_school_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide a ``SchoolService`` wired with school and audit repositories."""
    from app.modules.school.service import SchoolService

    return SchoolService(repo, audit)


def get_student_service(
    repo=Depends(_get_student_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide a ``StudentService`` wired with student and audit repositories."""
    from app.modules.students.service import StudentService

    return StudentService(repo, audit)


def get_fee_service(
    repo=Depends(_get_fee_repository),
    student_repo=Depends(_get_student_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide a ``FeeService`` wired with fee, student, and audit repositories."""
    from app.modules.fees.service import FeeService

    return FeeService(repo, student_repo, audit)


def get_payment_service(
    repo=Depends(_get_payment_repository),
    fee_repo=Depends(_get_fee_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide a ``PaymentService`` wired with payment, fee, and audit repositories."""
    from app.modules.payments.service import PaymentService

    return PaymentService(repo, fee_repo, audit)


def get_reminder_service(
    repo=Depends(_get_reminder_repository),
    audit=Depends(_get_audit_repository),
):
    """Provide a ``ReminderService`` wired with reminder and audit repositories."""
    from app.modules.reminders.service import ReminderService

    return ReminderService(repo, audit)


def get_report_service(
    fee_repo=Depends(_get_fee_repository),
    payment_repo=Depends(_get_payment_repository),
    student_repo=Depends(_get_student_repository),
):
    """Provide a ``ReportService`` wired with fee, payment, and student repositories."""
    from app.modules.reports.service import ReportService

    return ReportService(fee_repo, payment_repo, student_repo)
