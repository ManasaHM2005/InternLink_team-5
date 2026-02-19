from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from config import settings

connect_args = {}
if settings.DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False

engine = create_engine(settings.DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """Dependency to get database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def create_tables():
    """Create all database tables."""
    from models.user import User, UserProfile, Resume
    from models.recruiter import RecruiterProfile
    from models.job import Job
    from models.application import Application, ApplicationStatusHistory
    from models.social import Post, Comment, Like, Share, Follow
    from models.notification import Notification
    from models.interview import Interview, InterviewPrep
    from models.dispute import Dispute
    Base.metadata.create_all(bind=engine)
