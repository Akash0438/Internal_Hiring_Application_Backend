from datetime import datetime

from beanie import PydanticObjectId

from app.models.notification import Notification


async def create_notification(user_id: PydanticObjectId, message: str) -> Notification:
    notification = Notification(
        user_id=user_id,
        message=message,
        created_at=datetime.utcnow(),
    )
    await notification.insert()
    return notification
