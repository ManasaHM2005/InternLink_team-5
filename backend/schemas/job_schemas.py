from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class JobCreate(BaseModel):
    title: str
    description: str
    requirements: Optional[List[str]] = []
    skills_required: Optional[List[str]] = []
    location: Optional[str] = None
    is_remote: bool = False
    stipend_min: Optional[float] = None
    stipend_max: Optional[float] = None
    job_type: str = "internship"
    duration: Optional[str] = None
    openings: int = 1
    deadline: Optional[datetime] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[List[str]] = None
    skills_required: Optional[List[str]] = None
    location: Optional[str] = None
    is_remote: Optional[bool] = None
    stipend_min: Optional[float] = None
    stipend_max: Optional[float] = None
    job_type: Optional[str] = None
    duration: Optional[str] = None
    openings: Optional[int] = None
    deadline: Optional[datetime] = None
    is_active: Optional[bool] = None


class JobResponse(BaseModel):
    id: int
    recruiter_id: int
    title: str
    description: str
    requirements: List[str]
    skills_required: List[str]
    location: Optional[str]
    is_remote: bool
    stipend_min: Optional[float]
    stipend_max: Optional[float]
    job_type: str
    duration: Optional[str]
    openings: int
    is_approved: bool
    is_active: bool
    deadline: Optional[datetime]
    views_count: int
    created_at: datetime
    company_name: Optional[str] = None

    class Config:
        from_attributes = True


class JobSearchParams(BaseModel):
    query: Optional[str] = None
    location: Optional[str] = None
    skills: Optional[List[str]] = None
    stipend_min: Optional[float] = None
    stipend_max: Optional[float] = None
    job_type: Optional[str] = None
    is_remote: Optional[bool] = None
    sort_by: Optional[str] = "created_at"  # created_at, stipend, relevance
    page: int = 1
    page_size: int = 20
