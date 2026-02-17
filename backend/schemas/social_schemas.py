from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Post Schemas ---
class PostCreate(BaseModel):
    content: str
    media_url: Optional[str] = None


class PostResponse(BaseModel):
    id: int
    user_id: int
    content: str
    media_url: Optional[str]
    created_at: datetime
    author_name: Optional[str] = None
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    is_liked: bool = False

    class Config:
        from_attributes = True


# --- Comment Schemas ---
class CommentCreate(BaseModel):
    content: str


class CommentResponse(BaseModel):
    id: int
    post_id: int
    user_id: int
    content: str
    created_at: datetime
    author_name: Optional[str] = None

    class Config:
        from_attributes = True


# --- Follow Schemas ---
class FollowResponse(BaseModel):
    id: int
    user_id: int
    full_name: Optional[str] = None
    email: str

    class Config:
        from_attributes = True


class FollowStatsResponse(BaseModel):
    followers_count: int
    following_count: int
    is_following: bool = False
