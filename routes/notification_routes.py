from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models.user import User
from models.notification import Notification
from schemas.notification_schemas import NotificationResponse, UnreadCountResponse
from utils.dependencies import get_current_user
from services.notification_service import manager, mark_as_read, mark_all_as_read, get_unread_count
from services.auth_service import decode_access_token

router = APIRouter(prefix="/notifications", tags=["Notifications"])


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    is_read: bool = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's notifications."""
    query = db.query(Notification).filter(Notification.user_id == current_user.id)
    if is_read is not None:
        query = query.filter(Notification.is_read == is_read)
    notifications = query.order_by(Notification.created_at.desc()).offset(
        (page - 1) * page_size).limit(page_size).all()
    return notifications


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get count of unread notifications."""
    return UnreadCountResponse(unread_count=get_unread_count(db, current_user.id))


@router.put("/{notification_id}/read")
def read_notification(notification_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark a notification as read."""
    success = mark_as_read(db, notification_id, current_user.id)
    if not success:
        return {"message": "Notification not found"}
    return {"message": "Marked as read"}


@router.put("/read-all")
def read_all_notifications(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Mark all notifications as read."""
    count = mark_all_as_read(db, current_user.id)
    return {"message": f"Marked {count} notifications as read"}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...), db: Session = Depends(get_db)):
    """WebSocket endpoint for real-time notifications."""
    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001)
        return

    user_id = payload.get("user_id")
    if not user_id:
        await websocket.close(code=4001)
        return

    await manager.connect(websocket, user_id)
    try:
        while True:
            data = await websocket.receive_text()
            # Handle client messages if needed (e.g., mark as read)
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        manager.disconnect(websocket, user_id)
