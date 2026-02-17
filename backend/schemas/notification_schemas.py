from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    user_id: int
    type: str
    title: str
    message: str
    is_read: bool
    reference_id: Optional[int]
    reference_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    notification_ids: List[int]


class UnreadCountResponse(BaseModel):
    unread_count: int
