from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
import uuid
from database import get_db
from models.user import User, UserProfile
from models.application import Application
from models.job import Job
from models.interview import Interview, InterviewPrep
from models.recruiter import RecruiterProfile
from schemas.interview_schemas import InterviewSchedule, InterviewUpdate, InterviewResponse, VideoRoomResponse
from utils.dependencies import get_current_user, require_role
from services.notification_service import create_notification

router = APIRouter(prefix="/interviews", tags=["Interviews"])


@router.post("/schedule", response_model=InterviewResponse, status_code=201)
def schedule_interview(
    data: InterviewSchedule,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Schedule an interview for an application."""
    application = db.query(Application).filter(Application.id == data.application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    recruiter = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == current_user.id).first()
    if not job or job.recruiter_id != recruiter.id:
        raise HTTPException(status_code=403, detail="Access denied")

    room_id = uuid.uuid4().hex[:12]
    meeting_url = f"https://meet.internlink.com/room/{room_id}"
    meeting_token = uuid.uuid4().hex

    interview = Interview(
        application_id=data.application_id, scheduled_at=data.scheduled_at,
        duration_minutes=data.duration_minutes, meeting_url=meeting_url,
        meeting_token=meeting_token, notes=data.notes,
    )
    db.add(interview)

    # Update application status
    application.status = "interview_scheduled"
    db.commit()
    db.refresh(interview)

    # Notify applicant
    create_notification(db, application.user_id, "interview_scheduled",
        "Interview Scheduled",
        f"Interview scheduled for '{job.title}' on {data.scheduled_at.strftime('%Y-%m-%d %H:%M')}",
        reference_id=interview.id, reference_type="interview")

    profile = db.query(UserProfile).filter(UserProfile.user_id == application.user_id).first()
    return InterviewResponse(
        id=interview.id, application_id=interview.application_id,
        scheduled_at=interview.scheduled_at, duration_minutes=interview.duration_minutes,
        meeting_url=interview.meeting_url, status=interview.status,
        notes=interview.notes, feedback=interview.feedback, created_at=interview.created_at,
        applicant_name=profile.full_name if profile else None, job_title=job.title,
    )


@router.get("/{interview_id}", response_model=InterviewResponse)
def get_interview(interview_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get interview details."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    application = db.query(Application).filter(Application.id == interview.application_id).first()
    job = db.query(Job).filter(Job.id == application.job_id).first() if application else None
    profile = db.query(UserProfile).filter(UserProfile.user_id == application.user_id).first() if application else None

    return InterviewResponse(
        id=interview.id, application_id=interview.application_id,
        scheduled_at=interview.scheduled_at, duration_minutes=interview.duration_minutes,
        meeting_url=interview.meeting_url, status=interview.status,
        notes=interview.notes, feedback=interview.feedback, created_at=interview.created_at,
        applicant_name=profile.full_name if profile else None,
        job_title=job.title if job else None,
    )


@router.put("/{interview_id}", response_model=InterviewResponse)
def update_interview(interview_id: int, data: InterviewUpdate,
                     current_user: User = Depends(require_role("recruiter")), db: Session = Depends(get_db)):
    """Update interview details."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(interview, key, value)
    db.commit()
    db.refresh(interview)

    application = db.query(Application).filter(Application.id == interview.application_id).first()
    job = db.query(Job).filter(Job.id == application.job_id).first() if application else None
    profile = db.query(UserProfile).filter(UserProfile.user_id == application.user_id).first() if application else None

    return InterviewResponse(
        id=interview.id, application_id=interview.application_id,
        scheduled_at=interview.scheduled_at, duration_minutes=interview.duration_minutes,
        meeting_url=interview.meeting_url, status=interview.status,
        notes=interview.notes, feedback=interview.feedback, created_at=interview.created_at,
        applicant_name=profile.full_name if profile else None,
        job_title=job.title if job else None,
    )


@router.post("/{interview_id}/room", response_model=VideoRoomResponse)
def create_video_room(interview_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Create/get video interview room."""
    interview = db.query(Interview).filter(Interview.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    return VideoRoomResponse(
        room_id=interview.meeting_token[:12] if interview.meeting_token else uuid.uuid4().hex[:12],
        meeting_url=interview.meeting_url or f"https://meet.internlink.com/room/{uuid.uuid4().hex[:12]}",
        token=interview.meeting_token or uuid.uuid4().hex,
        expires_at=interview.scheduled_at + timedelta(hours=2) if interview.scheduled_at else datetime.utcnow() + timedelta(hours=2),
    )


@router.get("/upcoming/list", response_model=List[InterviewResponse])
def get_upcoming_interviews(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get upcoming interviews for the current user."""
    now = datetime.utcnow()

    if current_user.role == "recruiter":
        recruiter = db.query(RecruiterProfile).filter(RecruiterProfile.user_id == current_user.id).first()
        if not recruiter:
            return []
        job_ids = [j.id for j in db.query(Job).filter(Job.recruiter_id == recruiter.id).all()]
        app_ids = [a.id for a in db.query(Application).filter(Application.job_id.in_(job_ids)).all()] if job_ids else []
        interviews = db.query(Interview).filter(
            Interview.application_id.in_(app_ids), Interview.scheduled_at >= now,
            Interview.status == "scheduled").order_by(Interview.scheduled_at.asc()).all() if app_ids else []
    else:
        app_ids = [a.id for a in db.query(Application).filter(Application.user_id == current_user.id).all()]
        interviews = db.query(Interview).filter(
            Interview.application_id.in_(app_ids), Interview.scheduled_at >= now,
            Interview.status == "scheduled").order_by(Interview.scheduled_at.asc()).all() if app_ids else []

    result = []
    for i in interviews:
        app = db.query(Application).filter(Application.id == i.application_id).first()
        job = db.query(Job).filter(Job.id == app.job_id).first() if app else None
        profile = db.query(UserProfile).filter(UserProfile.user_id == app.user_id).first() if app else None
        result.append(InterviewResponse(
            id=i.id, application_id=i.application_id, scheduled_at=i.scheduled_at,
            duration_minutes=i.duration_minutes, meeting_url=i.meeting_url,
            status=i.status, notes=i.notes, feedback=i.feedback, created_at=i.created_at,
            applicant_name=profile.full_name if profile else None,
            job_title=job.title if job else None,
        ))
    return result
