"""Authentication API router.

Exposes endpoints for user login, logout, and retrieving the current
user's profile.  Logout invalidates all existing tokens by incrementing
the user's ``token_version``.
"""

from fastapi import APIRouter, Depends

from app.core.di import get_auth_service
from app.modules.auth.dependencies import get_current_user, get_current_user_token
from app.modules.auth.schemas import LoginRequest, LoginResponse, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    """Authenticate a user with email and password.

    Args:
        body: Login credentials.
        service: Injected auth service.

    Returns:
        A ``LoginResponse`` containing the user profile and JWT token.
    """
    user, token = await service.login(body.email, body.password)
    return LoginResponse(user=UserResponse.model_validate(user), token=token)


@router.get("/me", response_model=UserResponse)
async def me(current_user: UserResponse = Depends(get_current_user)):
    """Return the profile of the currently authenticated user.

    Args:
        current_user: The authenticated user resolved from the JWT.

    Returns:
        The caller's ``UserResponse`` profile.
    """
    return current_user


@router.post("/logout", status_code=204)
async def logout(
    token_data: dict = Depends(get_current_user_token),
    service: AuthService = Depends(get_auth_service),
):
    """Log out the current user by revoking all active tokens.

    Increments the user's ``token_version`` so that any previously
    issued JWTs are no longer accepted.

    Args:
        token_data: Decoded JWT claims containing the user ID.
        service: Injected auth service.
    """
    await service.logout(token_data["user_id"])
