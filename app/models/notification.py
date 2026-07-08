from datetime import datetime

from beanie import Document, PydanticObjectId
from pydantic import Field


class Notification(Document):
    user_id: PydanticObjectId
    message: str
    is_read: bool = False
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Settings:
        name = "notifications"
