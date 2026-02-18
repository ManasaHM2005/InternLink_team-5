from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from models.notification import Notification
from datetime import datetime
import json
import asyncio


# WebSocket connection manager for real-time notifications
class ConnectionManager:
    """Manages WebSocket connections for real-time notifications."""

    def __init__(self):
        self.active_connections: Dict[int, List] = {}  # user_id -> list of websockets

    async def connect(self, websocket, user_id: int):
        await websocket.accept()
        if user_id not in self.active_connections:
            self.active_connections[user_id] = []
        self.active_connections[user_id].append(websocket)

    def disconnect(self, websocket, user_id: int):
        if user_id in self.active_connections:
            self.active_connections[user_id].remove(websocket)
            if not self.active_connections[user_id]:
                del self.active_connections[user_id]

    async def send_notification(self, user_id: int, notification: dict):
        """Send a notification to a specific user via WebSocket."""
        if user_id in self.active_connections:
            message = json.dumps(notification)
            for connection in self.active_connections[user_id]:
                try:
                    await connection.send_text(message)
                except Exception:
                    pass

    async def broadcast(self, message: dict):
        """Broadcast a message to all connected users."""
        text = json.dumps(message)
        for user_id, connections in self.active_connections.items():
            for connection in connections:
                try:
                    await connection.send_text(text)
                except Exception:
                    pass


# Singleton connection manager
manager = ConnectionManager()


def create_notification(
    db: Session,
    user_id: int,
    notification_type: str,
    title: str,
    message: str,
    reference_id: Optional[int] = None,
    reference_type: Optional[str] = None
) -> Notification:
    """Create a new notification and attempt to send via WebSocket."""
    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        message=message,
        reference_id=reference_id,
        reference_type=reference_type,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    # Try to send via WebSocket
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(manager.send_notification(user_id, {
                "id": notification.id,
                "type": notification_type,
                "title": title,
                "message": message,
                "reference_id": reference_id,
                "reference_type": reference_type,
                "created_at": notification.created_at.isoformat(),
            }))
    except Exception:
        pass  # WebSocket delivery is best-effort

    return notification


def get_unread_count(db: Session, user_id: int) -> int:
    """Get the count of unread notifications for a user."""
    return db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).count()


def mark_as_read(db: Session, notification_id: int, user_id: int) -> bool:
    """Mark a notification as read."""
    notification = db.query(Notification).filter(
        Notification.id == notification_id,
        Notification.user_id == user_id
    ).first()
    if notification:
        notification.is_read = True
        db.commit()
        return True
    return False


def mark_all_as_read(db: Session, user_id: int) -> int:
    """Mark all notifications as read for a user. Returns count updated."""
    count = db.query(Notification).filter(
        Notification.user_id == user_id,
        Notification.is_read == False
    ).update({"is_read": True})
    db.commit()
    return count
