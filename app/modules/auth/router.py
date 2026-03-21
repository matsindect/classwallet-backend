"""Authentication API router.

Exposes endpoints for user login, logout, and retrieving the current
user's profile.  All responses are wrapped in the uniform API envelope
via ``success_response``.
"""

from fastapi import APIRouter, Depends

from app.core.di import get_auth_service
from app.core.response import success_response
from app.modules.auth.dependencies import get_current_user, get_current_user_token
from app.modules.auth.schemas import LoginData, LoginRequest, UserResponse
from app.modules.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/login")
async def login(body: LoginRequest, service: AuthService = Depends(get_auth_service)):
    """Authenticate a user with email and password.

    Returns a success envelope containing the user profile and JWT token.
    """
    user, token = await service.login(body.email, body.password)
    login_data = LoginData(user=UserResponse.from_user(user), token=token)
    return success_response(data=login_data.model_dump(by_alias=True))


@router.get("/me")
async def me(current_user: UserResponse = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return success_response(data=current_user.model_dump(by_alias=True))


@router.post("/logout")
async def logout(
    token_data: dict = Depends(get_current_user_token),
    service: AuthService = Depends(get_auth_service),
):
    """Log out the current user by revoking all active tokens.

    Increments the user's ``token_version`` so that any previously
    issued JWTs are no longer accepted.
    """
    await service.logout(token_data["user_id"])
    return success_response()
