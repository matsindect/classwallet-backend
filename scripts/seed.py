"""Development seed script for the Class Wallet backend.

Creates a single school (Greenfield Academy) with three users (admin,
finance, staff), five students across different grades, one fee structure
for Term 1 2026, corresponding invoices for each student, and payments
with varying amounts so that paid, partial, and unpaid statuses are all
represented.  Intended for local development and demo purposes only.
"""

import asyncio
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, engine, async_session_factory
from app.core.security import hash_password
from app.modules.school.models import School
from app.modules.auth.models import User
from app.modules.students.models import Student
from app.modules.fees.models import FeeStructure, StudentInvoice
from app.modules.payments.models import Payment


async def seed():
    """Populate the database with development seed data.

    Creates all tables via SQLAlchemy metadata, then inserts a school,
    three users (ADMIN, FINANCE, STAFF), five students, a fee structure,
    invoices, and payments.  The first two students are fully paid, the
    next two are partially paid, and the last student is unpaid.
    """
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        session: AsyncSession

        # School
        school_id = str(uuid.uuid4())
        school = School(
            id=school_id,
            name="Greenfield Academy",
            address="123 Education Lane, Knowledge City",
            phone="+1-555-0100",
            email="admin@greenfield.edu",
            currency="USD",
            timezone="America/New_York",
        )
        session.add(school)

        # Admin user
        admin_id = str(uuid.uuid4())
        admin = User(
            id=admin_id,
            school_id=school_id,
            email="admin@greenfield.edu",
            first_name="Admin",
            last_name="User",
            password_hash=hash_password("admin123"),
            role="ADMIN",
        )
        session.add(admin)

        # Finance user
        finance_id = str(uuid.uuid4())
        finance = User(
            id=finance_id,
            school_id=school_id,
            email="finance@greenfield.edu",
            first_name="Finance",
            last_name="Manager",
            password_hash=hash_password("finance123"),
            role="FINANCE",
        )
        session.add(finance)

        # Staff user
        staff_id = str(uuid.uuid4())
        staff = User(
            id=staff_id,
            school_id=school_id,
            email="staff@greenfield.edu",
            first_name="Staff",
            last_name="Member",
            password_hash=hash_password("staff123"),
            role="STAFF",
        )
        session.add(staff)

        # Students
        student_ids = []
        students_data = [
            ("Alice", "Johnson", "Grade 10", "alice.j@email.com"),
            ("Bob", "Smith", "Grade 10", "bob.s@email.com"),
            ("Carol", "Williams", "Grade 11", "carol.w@email.com"),
            ("David", "Brown", "Grade 11", "david.b@email.com"),
            ("Eve", "Davis", "Grade 12", "eve.d@email.com"),
        ]
        for first, last, grade, email in students_data:
            sid = str(uuid.uuid4())
            student_ids.append(sid)
            session.add(Student(
                id=sid,
                school_id=school_id,
                first_name=first,
                last_name=last,
                grade=grade,
                email=email,
                status="active",
            ))

        # Fee structures
        fs_id = str(uuid.uuid4())
        session.add(FeeStructure(
            id=fs_id,
            school_id=school_id,
            name="Tuition Fee - 2026 Term 1",
            description="First term tuition fee",
            amount=5000.00,
            currency="USD",
            academic_year="2026",
            term="Term 1",
            due_date="2026-04-01",
            is_published=True,
        ))

        # Invoices and payments for each student
        for i, sid in enumerate(student_ids):
            inv_id = str(uuid.uuid4())
            paid = 5000.00 if i < 2 else (2500.00 if i < 4 else 0.0)
            session.add(StudentInvoice(
                id=inv_id,
                school_id=school_id,
                student_id=sid,
                fee_structure_id=fs_id,
                invoice_number=f"INV-2026-{1001 + i}",
                amount=5000.00,
                amount_paid=paid,
                balance=5000.00 - paid,
                status="paid" if paid >= 5000 else ("partial" if paid > 0 else "unpaid"),
                due_date="2026-04-01",
            ))

            if paid > 0:
                session.add(Payment(
                    id=str(uuid.uuid4()),
                    school_id=school_id,
                    student_id=sid,
                    invoice_id=inv_id,
                    amount=paid,
                    method="bank_transfer" if i % 2 == 0 else "cash",
                    reference=f"PAY-{uuid.uuid4().hex[:8].upper()}",
                    status="completed",
                    created_by=finance_id,
                    paid_at=datetime.now(timezone.utc),
                ))

        await session.commit()
        print("Seed data created successfully!")
        print(f"  School: {school.name} (id: {school_id})")
        print(f"  Admin login: admin@greenfield.edu / admin123")
        print(f"  Finance login: finance@greenfield.edu / finance123")
        print(f"  Staff login: staff@greenfield.edu / staff123")
        print(f"  Students: {len(student_ids)}")
        print(f"  Fee structure: {fs_id}")


if __name__ == "__main__":
    asyncio.run(seed())
