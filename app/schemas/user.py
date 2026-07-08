from typing import Optional

from pydantic import BaseModel, EmailStr

from app.models.user import Role


class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    role: Role


class UpdateUserRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[Role] = None
    is_active: Optional[bool] = None
    can_create_portfolio_managers: Optional[bool] = None


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    role: str
    must_change_password: bool
    can_create_portfolio_managers: bool
    is_active: bool
    created_at: str
