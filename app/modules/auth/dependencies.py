"""FastAPI dependencies for JWT-based authentication.

Provides injectable dependency functions that extract the Bearer token
from incoming requests, decode and validate the JWT, and resolve the
corresponding :class:`~app.modules.auth.models.User` via
:class:`~app.modules.auth.service.AuthService`.  The validated user is
also attached to ``request.state.current_user`` for downstream access.
"""

import json

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.errors import AuthError
from app.core.security import decode_access_token
from app.modules.auth.schemas import UserResponse

bearer_scheme = HTTPBearer()


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> dict:
    """Decode the JWT Bearer token and return the embedded claims.

    Extracts the ``sub`` claim (a JSON string containing ``user_id`` and
    ``tv`` — token version) from the decoded JWT payload.

    Args:
        credentials: Bearer token credentials injected by FastAPI's
            ``HTTPBearer`` security scheme.

    Returns:
        A dict with keys ``user_id`` (str) and ``tv`` (int).

    Raises:
        AuthError: If the token is invalid, expired, or the payload
            cannot be parsed.
    """
    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise AuthError(message="Invalid or expired token")
    sub = payload.get("sub")
    if not sub:
        raise AuthError(message="Invalid token payload")
    try:
        data = json.loads(sub)
    except (json.JSONDecodeError, TypeError):
        raise AuthError(message="Invalid token payload")
    return data


async def get_current_user(
    request: Request,
    token_data: dict = Depends(get_current_user_token),
    session: AsyncSession = Depends(get_db_session),
) -> UserResponse:
    """Resolve and validate the currently authenticated user.

    Uses the token claims to load the user from the database, verify that
    the account is active, and confirm the token version has not been
    revoked.  The ORM user instance is stored on ``request.state`` for
    optional use in later middleware or route handlers.

    Args:
        request: The incoming FastAPI request (used to attach state).
        token_data: Decoded JWT claims from :func:`get_current_user_token`.
        session: Async database session.

    Returns:
        A :class:`UserResponse` Pydantic model representing the caller.

    Raises:
        AuthError: If the user is not found, inactive, or the token has
            been revoked.
    """
    from app.modules.auth.repository import AuthRepository
    from app.modules.auth.service import AuthService
    from app.modules.audit.repository import AuditRepository

    auth_repo = AuthRepository(session)
    audit_repo = AuditRepository(session)
    service = AuthService(auth_repo, audit_repo)
    user = await service.get_current_user(token_data["user_id"], token_data["tv"])
    request.state.current_user = user
    return UserResponse.model_validate(user)
