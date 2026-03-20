"""Business-logic layer for authentication and user management.

Coordinates login/logout flows, JWT creation, token-version validation,
and school-scoped user CRUD.  All mutating operations are audit-logged
via :class:`AuditRepository`.
"""

import json

from app.core.errors import AuthError, NotFoundError
from app.core.security import create_access_token, hash_password, verify_password
from app.modules.audit.repository import AuditRepository
from app.modules.auth.models import User
from app.modules.auth.repository import AuthRepository


class AuthService:
    """Service encapsulating authentication and user-management logic.

    Args:
        repo: Repository for user persistence operations.
        audit_repo: Repository for writing audit-log entries.
    """

    def __init__(self, repo: AuthRepository, audit_repo: AuditRepository):
        self.repo = repo
        self.audit_repo = audit_repo

    async def login(self, email: str, password: str) -> tuple[User, str]:
        """Authenticate a user and issue a JWT access token.

        The token's ``sub`` claim contains a JSON payload with the user ID
        and the current ``token_version``, enabling server-side revocation.

        Args:
            email: The user's email address.
            password: The plaintext password to verify.

        Returns:
            A tuple of the authenticated ``User`` and the signed JWT string.

        Raises:
            AuthError: If credentials are invalid or the account is deactivated.
        """
        user = await self.repo.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise AuthError(message="Invalid email or password")
        if not user.is_active:
            raise AuthError(message="Account is deactivated")

        token = create_access_token(
            subject=json.dumps({"user_id": user.id, "tv": user.token_version})
        )
        return user, token

    async def get_current_user(self, user_id: str, token_version: int) -> User:
        """Retrieve and validate the currently authenticated user.

        Checks that the user exists, is active, and that the token's
        version matches the stored version (i.e., the token has not been
        revoked by a logout).

        Args:
            user_id: UUID of the user extracted from the JWT.
            token_version: Token version from the JWT's ``sub`` claim.

        Returns:
            The validated ``User`` instance.

        Raises:
            AuthError: If the user is missing, inactive, or the token
                version does not match (revoked token).
        """
        user = await self.repo.get_by_id(user_id)
        if not user or not user.is_active:
            raise AuthError(message="User not found or inactive")
        if user.token_version != token_version:
            raise AuthError(message="Token has been revoked")
        return user

    async def logout(self, user_id: str) -> None:
        """Log out a user by incrementing their token version.

        All previously issued JWTs become invalid because their embedded
        ``tv`` value will no longer match the stored ``token_version``.

        Args:
            user_id: UUID of the user to log out.
        """
        await self.repo.increment_token_version(user_id)

    async def get_school_users(self, school_id: str) -> list[User]:
        """List all users belonging to a school.

        Args:
            school_id: UUID of the school.

        Returns:
            List of ``User`` instances, newest first.
        """
        return await self.repo.get_users_by_school(school_id)

    async def create_school_user(
        self,
        school_id: str,
        email: str,
        first_name: str,
        last_name: str,
        role_id: str,
        phone: str | None,
        actor_id: str,
    ) -> User:
        """Create a new user within a school.

        The user is assigned the default password ``changeme123`` and an
        audit log entry is recorded.

        Args:
            school_id: UUID of the school the new user belongs to.
            email: Unique email for the new user.
            first_name: User's first name.
            last_name: User's last name.
            role_id: UUID of the role to assign.
            phone: Optional phone number.
            actor_id: UUID of the user performing the action (for audit).

        Returns:
            The newly created ``User`` instance.

        Raises:
            ConflictError: If a user with the given email already exists.
        """
        existing = await self.repo.get_by_email(email)
        if existing:
            from app.core.errors import ConflictError

            raise ConflictError(message="A user with this email already exists")

        user = User(
            school_id=school_id,
            email=email,
            first_name=first_name,
            last_name=last_name,
            role_id=role_id,
            phone=phone,
            password_hash=hash_password("changeme123"),
        )
        user = await self.repo.create_user(user)

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="create",
            entity="user",
            entity_id=user.id,
        )

        # Re-fetch to get role relationship loaded
        return await self.repo.get_by_id(user.id)  # type: ignore[return-value]

    async def update_school_user(
        self, user_id: str, data: dict, actor_id: str, school_id: str
    ) -> User:
        """Update an existing school user's profile fields.

        Args:
            user_id: UUID of the user to update.
            data: Mapping of field names to new values.
            actor_id: UUID of the user performing the action (for audit).
            school_id: UUID of the school (for audit context).

        Returns:
            The updated ``User`` instance.

        Raises:
            NotFoundError: If no user with the given ID exists.
        """
        user = await self.repo.update_user(user_id, data)
        if not user:
            raise NotFoundError(message="User not found")

        await self.audit_repo.log(
            school_id=school_id,
            actor_id=actor_id,
            action="update",
            entity="user",
            entity_id=user_id,
        )

        # Re-fetch to get role relationship loaded
        return await self.repo.get_by_id(user_id)  # type: ignore[return-value]
