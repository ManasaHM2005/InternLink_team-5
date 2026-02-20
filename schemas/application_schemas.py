from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class ApplicationCreate(BaseModel):
    job_id: int
    resume_id: Optional[int] = None
    cover_letter: Optional[str] = None


class ApplicationStatusUpdate(BaseModel):
    status: str  # applied, shortlisted, rejected, interview_scheduled, selected
    notes: Optional[str] = None


class ApplicationResponse(BaseModel):
    id: int
    user_id: int
    job_id: int
    resume_id: Optional[int]
    cover_letter: Optional[str]
    status: str
    matching_score: Optional[float]
    applied_at: datetime
    updated_at: datetime
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    applicant_name: Optional[str] = None
    applicant_email: Optional[str] = None
    skills: Optional[List[str]] = []
    education: Optional[List[dict]] = []
    experience: Optional[List[dict]] = []

    class Config:
        from_attributes = True


class StatusHistoryResponse(BaseModel):
    id: int
    application_id: int
    old_status: Optional[str]
    new_status: str
    notes: Optional[str]
    changed_at: datetime

    class Config:
        from_attributes = True


class ApplicationTrackingResponse(BaseModel):
    application: ApplicationResponse
    status_history: List[StatusHistoryResponse]
    interviews: List[dict] = []
