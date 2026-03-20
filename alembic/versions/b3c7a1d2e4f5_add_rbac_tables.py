"""add_rbac_tables

Revision ID: b3c7a1d2e4f5
Revises: aa0aa0656797
Create Date: 2026-03-20 10:00:00.000000

"""

import uuid
from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from passlib.context import CryptContext

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# revision identifiers, used by Alembic.
revision: str = "b3c7a1d2e4f5"
down_revision: Union[str, None] = "aa0aa0656797"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# --- Seed data ---

PERMISSIONS = [
    # Global wildcard
    ("*", "Unrestricted access to all resources"),
    # Schools (system-level)
    ("schools.*", "Full access to school management"),
    ("schools.create", "Create new schools"),
    ("schools.read", "View all schools"),
    ("schools.update", "Update any school"),
    ("schools.delete", "Delete schools"),
    # School (own school profile)
    ("school.*", "Full access to own school profile"),
    ("school.read", "View own school profile"),
    ("school.update", "Update own school profile"),
    # Users
    ("users.*", "Full access to user management"),
    ("users.create", "Create users"),
    ("users.read", "View users"),
    ("users.update", "Update users"),
    # Students
    ("students.*", "Full access to student management"),
    ("students.create", "Create students"),
    ("students.read", "View students"),
    ("students.update", "Update students"),
    ("students.import", "Bulk import students from CSV"),
    # Fees
    ("fees.*", "Full access to fee management"),
    ("fees.create", "Create fee structures"),
    ("fees.read", "View fee structures"),
    ("fees.update", "Update fee structures"),
    ("fees.publish", "Publish fee structures"),
    # Invoices
    ("invoices.*", "Full access to invoice management"),
    ("invoices.create", "Generate invoices from fee structures"),
    ("invoices.read", "View invoices"),
    # Payments
    ("payments.*", "Full access to payment management"),
    ("payments.read", "View payments"),
    ("payments.create", "Record payments"),
    ("payments.reconcile", "View reconciliation summaries"),
    # Reminders
    ("reminders.*", "Full access to reminder management"),
    ("reminders.create", "Create reminder configurations"),
    ("reminders.read", "View reminder configurations and history"),
    ("reminders.update", "Update reminder configurations"),
    # Reports
    ("reports.*", "Full access to reports"),
    ("reports.read", "View financial and enrolment reports"),
    ("reports.export", "Export reports as CSV"),
    # Audit
    ("audit.*", "Full access to audit logs"),
    ("audit.read", "View audit log entries"),
    # Roles & Permissions
    ("roles.*", "Full access to role management"),
    ("roles.create", "Create roles"),
    ("roles.read", "View roles"),
    ("roles.update", "Update roles"),
    ("roles.delete", "Delete roles"),
    ("permissions.*", "Full access to permission management"),
    ("permissions.create", "Create new permissions"),
    ("permissions.read", "View available permissions"),
]

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

SUPER_ADMIN_EMAIL = "super@fundowallet.com"
SUPER_ADMIN_DEFAULT_PASSWORD = "Super@dmin2026!"


def upgrade() -> None:
    # 1. Create permissions table
    op.create_table(
        "permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("action", sa.String(100), unique=True, nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # 2. Create roles table
    op.create_table(
        "roles",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False),
        sa.Column("slug", sa.String(50), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("school_id", sa.String(36), sa.ForeignKey("schools.id"), nullable=True),
        sa.Column("is_system", sa.Boolean, default=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("slug", "school_id", name="uq_role_slug_school"),
    )

    # 3. Create role_permissions join table
    op.create_table(
        "role_permissions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "role_id",
            sa.String(36),
            sa.ForeignKey("roles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "permission_id",
            sa.String(36),
            sa.ForeignKey("permissions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    # 4. Seed permissions
    permissions_table = sa.table(
        "permissions",
        sa.column("id", sa.String),
        sa.column("action", sa.String),
        sa.column("description", sa.Text),
    )
    perm_ids = {}
    for action, description in PERMISSIONS:
        perm_id = str(uuid.uuid4())
        perm_ids[action] = perm_id
        op.execute(
            permissions_table.insert().values(
                id=perm_id, action=action, description=description
            )
        )

    # 5. Seed system roles and their permissions
    roles_table = sa.table(
        "roles",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("slug", sa.String),
        sa.column("description", sa.Text),
        sa.column("school_id", sa.String),
        sa.column("is_system", sa.Boolean),
    )
    role_perms_table = sa.table(
        "role_permissions",
        sa.column("id", sa.String),
        sa.column("role_id", sa.String),
        sa.column("permission_id", sa.String),
    )

    role_ids = {}
    for role_name, role_data in SYSTEM_ROLES.items():
        role_id = str(uuid.uuid4())
        role_ids[role_name] = role_id
        op.execute(
            roles_table.insert().values(
                id=role_id,
                name=role_name,
                slug=role_data["slug"],
                description=role_data["description"],
                school_id=None,
                is_system=True,
            )
        )
        for perm_action in role_data["permissions"]:
            op.execute(
                role_perms_table.insert().values(
                    id=str(uuid.uuid4()),
                    role_id=role_id,
                    permission_id=perm_ids[perm_action],
                )
            )

    # 6. Add role_id column to users (nullable initially)
    op.add_column("users", sa.Column("role_id", sa.String(36), nullable=True))

    # 7. Data migration: set role_id based on existing role string
    for role_name, role_id in role_ids.items():
        op.execute(
            sa.text(
                "UPDATE users SET role_id = :role_id WHERE role = :role_name"
            ).bindparams(role_id=role_id, role_name=role_name)
        )

    # 8. Make role_id NOT NULL and add FK constraint
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role_id", nullable=False)
        batch_op.create_foreign_key("fk_users_role_id", "roles", ["role_id"], ["id"])

    # 9. Make old role column nullable (kept for rollback safety)
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(20), nullable=True)

    # 10. Make school_id nullable on users and audit_logs (super_admin has no school)
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("school_id", existing_type=sa.String(36), nullable=True)
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("school_id", existing_type=sa.String(36), nullable=True)

    # 11. Seed the super_admin user
    now = datetime.now(timezone.utc).isoformat()
    users_table = sa.table(
        "users",
        sa.column("id", sa.String),
        sa.column("school_id", sa.String),
        sa.column("email", sa.String),
        sa.column("first_name", sa.String),
        sa.column("last_name", sa.String),
        sa.column("password_hash", sa.Text),
        sa.column("role", sa.String),
        sa.column("role_id", sa.String),
        sa.column("is_active", sa.Boolean),
        sa.column("token_version", sa.Integer),
        sa.column("created_at", sa.String),
        sa.column("updated_at", sa.String),
    )
    op.execute(
        users_table.insert().values(
            id=str(uuid.uuid4()),
            school_id=None,
            email=SUPER_ADMIN_EMAIL,
            first_name="Super",
            last_name="Admin",
            password_hash=_pwd_context.hash(SUPER_ADMIN_DEFAULT_PASSWORD),
            role=None,
            role_id=role_ids["SUPER_ADMIN"],
            is_active=True,
            token_version=0,
            created_at=now,
            updated_at=now,
        )
    )


def downgrade() -> None:
    # Delete seeded super_admin user (has no school)
    op.execute(sa.text("DELETE FROM users WHERE school_id IS NULL"))

    # Restore school_id to NOT NULL on users and audit_logs
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("school_id", existing_type=sa.String(36), nullable=False)
    with op.batch_alter_table("audit_logs") as batch_op:
        batch_op.alter_column("school_id", existing_type=sa.String(36), nullable=False)

    # Restore role column to NOT NULL
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("role", existing_type=sa.String(20), nullable=False)

    # Drop role_id FK and column
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_constraint("fk_users_role_id", type_="foreignkey")
        batch_op.drop_column("role_id")

    # Drop tables in reverse order
    op.drop_table("role_permissions")
    op.drop_table("roles")
    op.drop_table("permissions")
