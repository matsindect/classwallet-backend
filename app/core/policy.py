"""Role-based access control (RBAC) policy layer.

Defines the ``UserRole`` enum, a static permission matrix
(``PERMISSION_MAP``) that maps action strings to the set of roles that may
perform them, and an ``enforce()`` gate function that raises
``ForbiddenError`` when a role is not permitted to perform a given action.

Injected into routes that need authorization beyond authentication.
"""

import enum

from app.core.errors import ForbiddenError


class UserRole(str, enum.Enum):
    """Enumeration of user roles within the ClassWallet system.

    Attributes:
        ADMIN: Full system administrator with unrestricted access.
        FINANCE: Finance staff who can manage fees, payments, and reports.
        STAFF: General school staff with read-oriented access to students
            and payments.
    """

    ADMIN = "ADMIN"
    FINANCE = "FINANCE"
    STAFF = "STAFF"


# Permission matrix: action -> allowed roles
PERMISSION_MAP: dict[str, set[UserRole]] = {
    "manage_users": {UserRole.ADMIN},
    "manage_school": {UserRole.ADMIN},
    "manage_fees": {UserRole.ADMIN, UserRole.FINANCE},
    "manage_payments": {UserRole.ADMIN, UserRole.FINANCE},
    "view_payments": {UserRole.ADMIN, UserRole.FINANCE, UserRole.STAFF},
    "manage_students": {UserRole.ADMIN, UserRole.STAFF},
    "view_students": {UserRole.ADMIN, UserRole.FINANCE, UserRole.STAFF},
    "manage_reminders": {UserRole.ADMIN, UserRole.FINANCE},
    "view_reports": {UserRole.ADMIN, UserRole.FINANCE},
    "view_audit": {UserRole.ADMIN},
}


def enforce(role: UserRole | str, action: str) -> None:
    """Assert that a role is permitted to perform an action.

    Looks up the action in ``PERMISSION_MAP`` and raises ``ForbiddenError``
    if the role is not in the allowed set.

    Args:
        role: The user's role, either as a ``UserRole`` enum member or its
            string value.
        action: The action key to check (must exist in ``PERMISSION_MAP``).

    Raises:
        ForbiddenError: If the role is not authorised for the action.
        ValueError: If ``role`` is a string that does not match any
            ``UserRole`` member.
    """
    if isinstance(role, str):
        role = UserRole(role)
    allowed = PERMISSION_MAP.get(action, set())
    if role not in allowed:
        raise ForbiddenError(message=f"Role '{role.value}' is not allowed to perform '{action}'")
