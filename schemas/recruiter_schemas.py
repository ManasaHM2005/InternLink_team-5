from pydantic import BaseModel
from typing import Optional


class RecruiterProfileCreate(BaseModel):
    company_name: str
    company_description: Optional[str] = None
    website: Optional[str] = None
    industry: Optional[str] = None
    company_size: Optional[str] = None
    headquarters: Optional[str] = None


class RecruiterProfileUpdate(RecruiterProfileCreate):
    company_name: Optional[str] = None


class RecruiterProfileResponse(BaseModel):
    id: int
    user_id: int
    company_name: str
    company_description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    company_size: Optional[str]
    company_logo: Optional[str]
    headquarters: Optional[str]

    class Config:
        from_attributes = True
