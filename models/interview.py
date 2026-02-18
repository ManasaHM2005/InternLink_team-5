from sqlalchemy import Column, Integer, String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Interview(Base):
    __tablename__ = "interviews"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=30)
    meeting_url = Column(String(500), nullable=True)
    meeting_token = Column(String(500), nullable=True)
    status = Column(String(50), default="scheduled")  # scheduled, in_progress, completed, cancelled
    notes = Column(Text, nullable=True)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    application = relationship("Application", back_populates="interviews")


class InterviewPrep(Base):
    __tablename__ = "interview_preps"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    questions = Column(JSON, default=list)
    # [{"question": "...", "category": "technical/behavioral", "difficulty": "easy/medium/hard", "sample_answer": "..."}]
    tips = Column(JSON, default=list)
    # ["Tip 1", "Tip 2", ...]
    focus_areas = Column(JSON, default=list)
    # ["Data Structures", "System Design", ...]
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    job = relationship("Job")
