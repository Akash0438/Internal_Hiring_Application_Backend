from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import User
from app.schemas.auth import ChangePasswordRequest, LoginRequest, TokenUserResponse, UserResponse
from app.services.auth_service import create_access_token, get_current_user
from app.utils.password import hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenUserResponse)
async def login(body: LoginRequest):
    user = await User.find_one(User.email == body.email)
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(
        {"sub": str(user.id), "role": user.role, "must_change_password": user.must_change_password}
    )
    return TokenUserResponse(
        access_token=token,
        id=str(user.id),
        name=user.name,
        email=user.email,
        role=user.role,
        must_change_password=user.must_change_password,
        can_create_portfolio_managers=user.can_create_portfolio_managers,
        is_active=user.is_active,
    )


@router.post("/logout")
async def logout():
    # Token is stored client-side; client discards it on logout
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


@router.post("/change-password", response_model=TokenUserResponse)
async def change_password(
    body: ChangePasswordRequest,
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

    # Re-issue token with must_change_password=False, return it in body
    token = create_access_token(
        {"sub": str(current_user.id), "role": current_user.role, "must_change_password": False}
    )
    return TokenUserResponse(
        access_token=token,
        id=str(current_user.id),
        name=current_user.name,
        email=current_user.email,
        role=current_user.role,
        must_change_password=False,
        can_create_portfolio_managers=current_user.can_create_portfolio_managers,
        is_active=current_user.is_active,
    )
