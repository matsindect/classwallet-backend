"""Role-based access control (RBAC) policy layer.

Provides the ``enforce()`` gate function that checks whether the current
user has the required permission.  Permissions are loaded from the
database into ``UserResponse.permissions`` during authentication, so
no database access is needed at authorisation time.

Supports granular ``resource.action`` permissions with wildcards:

* ``students.create`` — exact match
* ``students.*`` — matches any action on the ``students`` resource
* ``*`` — matches everything (super admin)
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from app.core.errors import ForbiddenError

if TYPE_CHECKING:
    from app.modules.auth.schemas import UserResponse


def _has_permission(user_permissions: list[str], required: str) -> bool:
    """Check if any user permission satisfies the required permission.

    Matching rules (checked in order):
    1. Global wildcard ``*`` grants everything.
    2. Resource wildcard ``resource.*`` grants any action on that resource.
    3. Exact match ``resource.action``.
    """
    for perm in user_permissions:
        if perm == "*":
            return True
        if perm == required:
            return True
        # resource wildcard: "students.*" matches "students.create"
        if perm.endswith(".*"):
            resource = perm[:-2]  # "students"
            if required.startswith(resource + "."):
                return True
    return False


def enforce(user: UserResponse, action: str) -> None:
    """Assert that the authenticated user has a specific permission.

    Checks the ``permissions`` list pre-loaded on the user response
    object using wildcard-aware matching.  Raises ``ForbiddenError``
    if the permission is not satisfied.

    Args:
        user: The authenticated user with pre-loaded permissions.
        action: The permission to check (e.g. ``"students.create"``).

    Raises:
        ForbiddenError: If the user does not have the required permission.
    """
    if not _has_permission(user.permissions, action):
        raise ForbiddenError(
            message=f"Role '{user.role}' is not allowed to perform '{action}'"
        )
