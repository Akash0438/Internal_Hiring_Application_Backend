from datetime import datetime

from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.user import Role, User
from app.schemas.user import CreateUserRequest, UpdateUserRequest, UserResponse
from app.services.auth_service import require_role
from app.services import email_service
from app.utils.password import generate_temp_password, hash_password

router = APIRouter(prefix="/users", tags=["users"])


def _fmt_user(u: User) -> UserResponse:
    return UserResponse(
        id=str(u.id),
        name=u.name,
        email=u.email,
        phone=u.phone,
        role=u.role,
        must_change_password=u.must_change_password,
        can_create_portfolio_managers=u.can_create_portfolio_managers,
        is_active=u.is_active,
        created_at=u.created_at.isoformat(),
    )


@router.get("/", response_model=list[UserResponse])
async def list_users(_: User = Depends(require_role(Role.ADMIN))):
    users = await User.find_all().to_list()
    return [_fmt_user(u) for u in users]


@router.get("/hiring-managers", response_model=list[UserResponse])
async def list_hiring_managers(current_user: User = Depends(require_role(Role.MAIN_MANAGER, Role.ADMIN))):
    """Return all active Hiring Managers — kept for backwards compatibility."""
    users = await User.find(User.role == Role.HIRING_MANAGER, User.is_active == True).to_list()  # noqa: E712
    return [_fmt_user(u) for u in users]


@router.get("/assignable-users", response_model=list[UserResponse])
async def list_assignable_users(current_user: User = Depends(require_role(Role.MAIN_MANAGER, Role.ADMIN))):
    """Return all active Hiring Managers AND Portfolio Managers — shown in the Assign Interview dropdown."""
    users = await User.find(
        {"role": {"$in": [Role.HIRING_MANAGER.value, Role.MAIN_MANAGER.value]}, "is_active": True}
    ).to_list()
    return [_fmt_user(u) for u in users]


@router.post("/", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    body: CreateUserRequest,
    current_user: User = Depends(require_role(Role.ADMIN)),
):
    existing = await User.find_one(User.email == body.email)
    if existing:
        raise HTTPException(status_code=400, detail="A user with this email already exists")

    temp_password = generate_temp_password()
    user = User(
        name=body.name,
        email=body.email,
        phone=body.phone,
        password=hash_password(temp_password),
        role=body.role,
        must_change_password=True,
        created_by_id=str(current_user.id),
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await user.insert()
    email_service.send_welcome_email(user.email, user.name, temp_password)
    return _fmt_user(user)


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    _: User = Depends(require_role(Role.ADMIN)),
):
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if body.name is not None:
        user.name = body.name
    if body.phone is not None:
        user.phone = body.phone
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.can_create_portfolio_managers is not None:
        user.can_create_portfolio_managers = body.can_create_portfolio_managers

    user.updated_at = datetime.utcnow()
    await user.save()
    return _fmt_user(user)


@router.post("/{user_id}/reset-password")
async def reset_password(
    user_id: str,
    _: User = Depends(require_role(Role.ADMIN)),
):
    user = await User.get(PydanticObjectId(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    temp_password = generate_temp_password()
    user.password = hash_password(temp_password)
    user.must_change_password = True
    user.updated_at = datetime.utcnow()
    await user.save()
    email_service.send_password_reset_email(user.email, user.name, temp_password)
    return {"message": "Password reset successfully"}
