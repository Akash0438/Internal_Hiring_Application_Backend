from typing import Optional

from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    new_password: str
    current_password: Optional[str] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    must_change_password: bool
    can_create_portfolio_managers: bool
    is_active: bool


class TokenUserResponse(UserResponse):
    """UserResponse plus a Bearer token — returned by login and change-password."""
    access_token: str
