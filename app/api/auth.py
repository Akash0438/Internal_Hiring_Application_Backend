from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.config import settings
from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, UserResponse
from app.services.auth_service import create_access_token, get_current_user
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

COOKIE_NAME = "access_token"
COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60


def _set_auth_cookie(response: Response, token: str) -> None:
    is_prod = settings.ENVIRONMENT == "production"
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=COOKIE_MAX_AGE,
        samesite="none" if is_prod else "lax",
        secure=is_prod,
        path="/",
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response):
    user = await User.find_one(User.email == body.email)
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(
        {"sub": str(user.id), "role": user.role, "must_change_password": user.must_change_password}
    )
    _set_auth_cookie(response, token)
    return UserResponse(
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
        must_change_password=user.must_change_password,
        can_create_portfolio_managers=user.can_create_portfolio_managers,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie(key=COOKIE_NAME, path="/")
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def me(current_user: User = Depends(get_current_user)):
    return UserResponse(
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        must_change_password=current_user.must_change_password,
        can_create_portfolio_managers=current_user.can_create_portfolio_managers,
        is_active=current_user.is_active,
    )


@router.post("/change-password")
async def change_password(
    body: ChangePasswordRequest,
    response: Response,
    current_user: User = Depends(get_current_user),
):
    if len(body.new_password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    # Voluntary change requires current password verification
    if not current_user.must_change_password:
        if not body.current_password:
            raise HTTPException(status_code=400, detail="Current password is required")
        if not verify_password(body.current_password, current_user.password):
            raise HTTPException(status_code=400, detail="Current password is incorrect")

    current_user.password = hash_password(body.new_password)
    current_user.must_change_password = False
    await current_user.save()

    # Re-issue token with updated must_change_password=False
    token = create_access_token(
        {"sub": str(current_user.id), "role": current_user.role, "must_change_password": False}
    )
    _set_auth_cookie(response, token)
    return {"message": "Password changed successfully"}
