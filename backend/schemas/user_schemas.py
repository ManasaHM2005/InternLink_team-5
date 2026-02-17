from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# --- Auth Schemas ---
class UserRegister(BaseModel):
    email: EmailStr
    password: str
    role: str = "user"  # user, recruiter


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    role: str


# --- User Profile Schemas ---
class UserProfileCreate(BaseModel):
    full_name: Optional[str] = None
    bio: Optional[str] = None
    skills: Optional[List[str]] = []
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    phone: Optional[str] = None
    education: Optional[List[dict]] = []
    experience: Optional[List[dict]] = []


class UserProfileUpdate(UserProfileCreate):
    pass


class UserProfileResponse(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str]
    bio: Optional[str]
    skills: List[str]
    location: Optional[str]
    profile_picture: Optional[str]
    linkedin_url: Optional[str]
    github_url: Optional[str]
    phone: Optional[str]
    education: List[dict]
    experience: List[dict]

    class Config:
        from_attributes = True


class UserResponse(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    created_at: datetime
    profile: Optional[UserProfileResponse] = None

    class Config:
        from_attributes = True


# --- Resume Schemas ---
class ResumeResponse(BaseModel):
    id: int
    user_id: int
    filename: str
    file_size: Optional[int]
    parsed_skills: List[str]
    is_primary: bool
    uploaded_at: datetime

    class Config:
        from_attributes = True
