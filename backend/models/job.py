from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Float, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    recruiter_id = Column(Integer, ForeignKey("recruiter_profiles.id"), nullable=False)
    title = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=False)
    requirements = Column(JSON, default=list)  # ["2 years exp", "CS degree", ...]
    skills_required = Column(JSON, default=list)  # ["Python", "Django", ...]
    location = Column(String(255), nullable=True, index=True)
    is_remote = Column(Boolean, default=False)
    stipend_min = Column(Float, nullable=True)
    stipend_max = Column(Float, nullable=True)
    job_type = Column(String(50), nullable=False, default="internship")  # internship, full-time, part-time
    duration = Column(String(100), nullable=True)  # e.g., "3 months", "6 months"
    openings = Column(Integer, default=1)
    is_approved = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    deadline = Column(DateTime, nullable=True)
    views_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    recruiter = relationship("RecruiterProfile", back_populates="jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
