from datetime import datetime
from enum import Enum
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field
from pymongo import IndexModel, ASCENDING


class Role(str, Enum):
    ADMIN = "ADMIN"
    MAIN_MANAGER = "PORTFOLIO_MANAGER"
    HIRING_MANAGER = "HIRING_MANAGER"


class User(Document):
    name: str
    email: Indexed(str, unique=True)  # type: ignore[valid-type]
    phone: Optional[str] = None
    password: str
    role: Role
    must_change_password: bool = True
    can_create_portfolio_managers: bool = False
    is_active: bool = True
    created_by_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "users"
        indexes = [
            IndexModel([("email", ASCENDING)], unique=True),
        ]
