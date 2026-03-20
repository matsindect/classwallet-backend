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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import Base, engine, async_session_factory
from app.core.security import hash_password
from app.modules.school.models import School
from app.modules.auth.models import User
from app.modules.rbac.models import Permission, Role, RolePermission
from app.modules.students.models import Student
from app.modules.fees.models import FeeStructure, StudentInvoice
from app.modules.payments.models import Payment

# Permission definitions (resource.action format with wildcards)
PERMISSIONS = [
    ("*", "Unrestricted access to all resources"),
    ("schools.*", "Full access to school management"),
    ("schools.create", "Create new schools"),
    ("schools.read", "View all schools"),
    ("schools.update", "Update any school"),
    ("schools.delete", "Delete schools"),
    ("school.*", "Full access to own school profile"),
    ("school.read", "View own school profile"),
    ("school.update", "Update own school profile"),
    ("users.*", "Full access to user management"),
    ("users.create", "Create users"),
    ("users.read", "View users"),
    ("users.update", "Update users"),
    ("students.*", "Full access to student management"),
    ("students.create", "Create students"),
    ("students.read", "View students"),
    ("students.update", "Update students"),
    ("students.import", "Bulk import students from CSV"),
    ("fees.*", "Full access to fee management"),
    ("fees.create", "Create fee structures"),
    ("fees.read", "View fee structures"),
    ("fees.update", "Update fee structures"),
    ("fees.publish", "Publish fee structures"),
    ("invoices.*", "Full access to invoice management"),
    ("invoices.create", "Generate invoices from fee structures"),
    ("invoices.read", "View invoices"),
    ("payments.*", "Full access to payment management"),
    ("payments.read", "View payments"),
    ("payments.create", "Record payments"),
    ("payments.reconcile", "View reconciliation summaries"),
    ("reminders.*", "Full access to reminder management"),
    ("reminders.create", "Create reminder configurations"),
    ("reminders.read", "View reminder configurations and history"),
    ("reminders.update", "Update reminder configurations"),
    ("reports.*", "Full access to reports"),
    ("reports.read", "View financial and enrolment reports"),
    ("reports.export", "Export reports as CSV"),
    ("audit.*", "Full access to audit logs"),
    ("audit.read", "View audit log entries"),
    ("roles.*", "Full access to role management"),
    ("roles.create", "Create roles"),
    ("roles.read", "View roles"),
    ("roles.update", "Update roles"),
    ("roles.delete", "Delete roles"),
    ("permissions.*", "Full access to permission management"),
    ("permissions.create", "Create new permissions"),
    ("permissions.read", "View available permissions"),
]

# Role-to-permission mappings (wildcards resolved by enforce())
SYSTEM_ROLES = {
    "SUPER_ADMIN": {
        "slug": "super-admin",
        "description": "System-wide super administrator with unrestricted access",
        "permissions": ["*"],
    },
    "ADMIN": {
        "slug": "admin",
        "description": "Full school administrator with unrestricted school-level access",
        "permissions": [
            "school.*", "users.*", "students.*", "fees.*",
            "invoices.*", "payments.*", "reminders.*",
            "reports.*", "audit.*", "roles.*", "permissions.*",
        ],
    },
    "FINANCE": {
        "slug": "finance",
        "description": "Finance staff who can manage fees, payments, and reports",
        "permissions": [
            "fees.*", "invoices.*",
            "payments.read", "payments.create", "payments.reconcile",
            "students.read",
            "reminders.*",
            "reports.*",
        ],
    },
    "STAFF": {
        "slug": "staff",
        "description": "General school staff with read-oriented access",
        "permissions": [
            "payments.read",
            "students.create", "students.read", "students.update", "students.import",
        ],
    },
}


async def seed_rbac(session: AsyncSession) -> dict[str, str]:
    """Seed permissions and system roles. Returns a map of role name to role ID."""
    # Create permissions (idempotent)
    perm_ids: dict[str, str] = {}
    for action, description in PERMISSIONS:
        existing = await session.execute(
            select(Permission).where(Permission.action == action)
        )
        perm = existing.scalar_one_or_none()
        if perm:
            perm_ids[action] = perm.id
        else:
            perm = Permission(action=action, description=description)
            session.add(perm)
            await session.flush()
            perm_ids[action] = perm.id

    # Create system roles (idempotent)
    role_ids: dict[str, str] = {}
    for role_name, role_data in SYSTEM_ROLES.items():
        existing = await session.execute(
            select(Role).where(Role.slug == role_data["slug"], Role.school_id.is_(None))
        )
        role = existing.scalar_one_or_none()
        if not role:
            role = Role(
                name=role_name,
                slug=role_data["slug"],
                description=role_data["description"],
                school_id=None,
                is_system=True,
            )
            session.add(role)
            await session.flush()

        role_ids[role_name] = role.id

        # Assign permissions to role
        for perm_action in role_data["permissions"]:
            existing_rp = await session.execute(
                select(RolePermission).where(
                    RolePermission.role_id == role.id,
                    RolePermission.permission_id == perm_ids[perm_action],
                )
            )
            if not existing_rp.scalar_one_or_none():
                session.add(
                    RolePermission(
                        role_id=role.id,
                        permission_id=perm_ids[perm_action],
                    )
                )

    await session.flush()
    return role_ids


async def seed():
    """Populate the database with development seed data.

    Creates all tables via SQLAlchemy metadata, then inserts RBAC data,
    a school, three users (ADMIN, FINANCE, STAFF), five students, a fee
    structure, invoices, and payments.
    """
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session_factory() as session:
        session: AsyncSession

        # Seed RBAC first
        role_ids = await seed_rbac(session)

        # Super Admin (system-wide, no school)
        super_admin = User(
            school_id=None,
            email="super@fundowallet.com",
            first_name="Super",
            last_name="Admin",
            password_hash=hash_password("Super@dmin2026!"),
            role_id=role_ids["SUPER_ADMIN"],
        )
        session.add(super_admin)

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
            role_id=role_ids["ADMIN"],
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
            role_id=role_ids["FINANCE"],
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
            role_id=role_ids["STAFF"],
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
        print(f"  Super Admin login: super@fundowallet.com / Super@dmin2026!")
        print(f"  School: {school.name} (id: {school_id})")
        print(f"  Admin login: admin@greenfield.edu / admin123")
        print(f"  Finance login: finance@greenfield.edu / finance123")
        print(f"  Staff login: staff@greenfield.edu / staff123")
        print(f"  Students: {len(student_ids)}")
        print(f"  Fee structure: {fs_id}")
        print(f"  Roles: {list(role_ids.keys())}")
        print(f"  Permissions: {len(PERMISSIONS)}")


if __name__ == "__main__":
    asyncio.run(seed())
