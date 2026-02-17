from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Dispute(Base):
    __tablename__ = "disputes"

    id = Column(Integer, primary_key=True, index=True)
    filed_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    against_user = Column(Integer, ForeignKey("users.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    subject = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    status = Column(String(50), default="open")  # open, under_review, resolved, dismissed
    admin_notes = Column(Text, nullable=True)
    resolution = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    resolved_at = Column(DateTime, nullable=True)

    # Relationships
    filed_by_user = relationship("User", foreign_keys=[filed_by])
    against = relationship("User", foreign_keys=[against_user])
    job = relationship("Job")
