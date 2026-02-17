from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Admin User Management ---
class AdminUserUpdate(BaseModel):
    is_active: Optional[bool] = None
    role: Optional[str] = None


class AdminJobApproval(BaseModel):
    is_approved: bool
    notes: Optional[str] = None


# --- Dispute Schemas ---
class DisputeCreate(BaseModel):
    against_user: Optional[int] = None
    job_id: Optional[int] = None
    subject: str
    description: str


class DisputeUpdate(BaseModel):
    status: str  # open, under_review, resolved, dismissed
    admin_notes: Optional[str] = None
    resolution: Optional[str] = None


class DisputeResponse(BaseModel):
    id: int
    filed_by: int
    against_user: Optional[int]
    job_id: Optional[int]
    subject: str
    description: str
    status: str
    admin_notes: Optional[str]
    resolution: Optional[str]
    created_at: datetime
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


# --- Analytics Schemas ---
class PlatformAnalytics(BaseModel):
    total_users: int
    total_recruiters: int
    total_jobs: int
    total_applications: int
    active_jobs: int
    pending_approvals: int
    total_disputes: int
    open_disputes: int
    users_this_month: int
    jobs_this_month: int
    applications_this_month: int
    top_skills: List[dict] = []
    application_status_breakdown: dict = {}
