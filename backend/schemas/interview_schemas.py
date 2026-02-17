from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class InterviewSchedule(BaseModel):
    application_id: int
    scheduled_at: datetime
    duration_minutes: int = 30
    notes: Optional[str] = None


class InterviewUpdate(BaseModel):
    scheduled_at: Optional[datetime] = None
    duration_minutes: Optional[int] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    feedback: Optional[str] = None


class InterviewResponse(BaseModel):
    id: int
    application_id: int
    scheduled_at: datetime
    duration_minutes: int
    meeting_url: Optional[str]
    status: str
    notes: Optional[str]
    feedback: Optional[str]
    created_at: datetime
    applicant_name: Optional[str] = None
    job_title: Optional[str] = None

    class Config:
        from_attributes = True


class VideoRoomResponse(BaseModel):
    room_id: str
    meeting_url: str
    token: str
    expires_at: datetime
