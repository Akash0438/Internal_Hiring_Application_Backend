from beanie import PydanticObjectId
from fastapi import APIRouter, Depends, HTTPException, status

from app.models.notification import Notification
from app.models.user import User
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("/")
async def list_notifications(
    unread_only: bool = False,
    current_user: User = Depends(get_current_user),
):
    query = Notification.find(Notification.user_id == current_user.id)
    if unread_only:
        query = Notification.find(
            Notification.user_id == current_user.id,
            Notification.is_read == False,  # noqa: E712
        )
    notifications = await query.sort(-Notification.created_at).limit(50).to_list()
    return [
        {
            "id": str(n.id),
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.isoformat(),
        }
        for n in notifications
    ]


@router.patch("/read-all")
async def mark_all_read(current_user: User = Depends(get_current_user)):
    await Notification.find(
        Notification.user_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    ).update({"$set": {"is_read": True}})
    return {"message": "All notifications marked as read"}


@router.patch("/{notification_id}/read")
async def mark_as_read(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    n = await Notification.get(PydanticObjectId(notification_id))
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(n.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    n.is_read = True
    await n.save()
    return {"message": "Marked as read"}


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: str,
    current_user: User = Depends(get_current_user),
):
    """Dismiss (permanently delete) a single notification."""
    n = await Notification.get(PydanticObjectId(notification_id))
    if not n:
        raise HTTPException(status_code=404, detail="Notification not found")
    if str(n.user_id) != str(current_user.id):
        raise HTTPException(status_code=403, detail="Access denied")
    await n.delete()


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_all_read(current_user: User = Depends(get_current_user)):
    """Delete all read notifications for the current user."""
    await Notification.find(
        Notification.user_id == current_user.id,
        Notification.is_read == True,  # noqa: E712
    ).delete()
