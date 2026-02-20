from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models.user import User, UserProfile, Resume
from models.job import Job
from models.application import Application, ApplicationStatusHistory
from models.recruiter import RecruiterProfile
from schemas.job_schemas import JobCreate, JobUpdate, JobResponse
from schemas.application_schemas import ApplicationStatusUpdate, ApplicationResponse
from schemas.recruiter_schemas import RecruiterProfileCreate, RecruiterProfileUpdate, RecruiterProfileResponse
from utils.dependencies import get_current_user, require_role
from services.analytics_service import get_recruiter_analytics
from services.notification_service import create_notification
import os

router = APIRouter(prefix="/recruiter", tags=["Recruiter"])

@router.get("/debug/system-state")
def debug_system_state(db: Session = Depends(get_db)):
    return {
        "users_count": db.query(User).count(),
        "jobs_count": db.query(Job).count(),
        "applications_count": db.query(Application).count(),
        "recruiter_profiles_count": db.query(RecruiterProfile).count(),
        "all_jobs": [{"id": j.id, "title": j.title, "recruiter_id": j.recruiter_id} for j in db.query(Job).all()],
        "all_apps": [{"id": a.id, "job_id": a.job_id, "user_id": a.user_id} for a in db.query(Application).all()]
    }


# --- Recruiter Profile ---
@router.get("/profile", response_model=RecruiterProfileResponse)
def get_recruiter_profile(
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Get recruiter's company profile."""
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")
    return profile


@router.put("/profile", response_model=RecruiterProfileResponse)
def update_recruiter_profile(
    profile_data: RecruiterProfileUpdate,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Update recruiter's company profile."""
    profile = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()

    if not profile:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


# --- Job Posting ---
@router.post("/jobs", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(
    job_data: JobCreate,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Post a new job/internship."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found. Update your profile first.")

    job = Job(
        recruiter_id=recruiter.id,
        **job_data.model_dump()
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    response = JobResponse(
        **{c.name: getattr(job, c.name) for c in job.__table__.columns},
        company_name=recruiter.company_name,
    )
    return response


@router.get("/jobs", response_model=List[JobResponse])
def get_my_jobs(
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Get all jobs posted by the recruiter."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not recruiter:
        return []

    jobs = db.query(Job).filter(
        Job.recruiter_id == recruiter.id
    ).order_by(Job.created_at.desc()).all()

    return [
        JobResponse(
            **{c.name: getattr(j, c.name) for c in j.__table__.columns},
            company_name=recruiter.company_name,
        )
        for j in jobs
    ]


@router.put("/jobs/{job_id}", response_model=JobResponse)
def update_job(
    job_id: int,
    job_data: JobUpdate,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Update a job posting."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    job = db.query(Job).filter(
        Job.id == job_id, Job.recruiter_id == recruiter.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    update_data = job_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(job, key, value)

    db.commit()
    db.refresh(job)

    return JobResponse(
        **{c.name: getattr(job, c.name) for c in job.__table__.columns},
        company_name=recruiter.company_name,
    )


# --- Applicants ---
@router.get("/jobs/{job_id}/applicants", response_model=List[ApplicationResponse])
def get_applicants(
    job_id: int,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """View all applicants for a specific job."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    job = db.query(Job).filter(
        Job.id == job_id, Job.recruiter_id == recruiter.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    applications = db.query(Application).filter(
        Application.job_id == job_id
    ).order_by(Application.matching_score.desc().nullslast()).all()

    result = []
    for app in applications:
        user = db.query(User).filter(User.id == app.user_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == app.user_id).first()
        resume = db.query(Resume).filter(Resume.id == app.resume_id).first() if app.resume_id else None
        
        # Combine skills from profile and resume
        skills = set()
        if profile and profile.skills:
            skills.update(profile.skills)
        if resume and resume.parsed_skills:
            skills.update(resume.parsed_skills)

        result.append(ApplicationResponse(
            id=app.id,
            user_id=app.user_id,
            job_id=app.job_id,
            resume_id=app.resume_id,
            cover_letter=app.cover_letter,
            status=app.status,
            matching_score=app.matching_score,
            applied_at=app.applied_at,
            updated_at=app.updated_at,
            job_title=job.title,
            applicant_name=profile.full_name if profile else None,
            applicant_email=user.email if user else None,
            skills=list(skills),
            education=profile.education if profile else [],
            experience=profile.experience if profile else []
        ))

    return result


@router.get("/applicants", response_model=List[ApplicationResponse])
def get_all_applicants(
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """View all applicants for all jobs posted by the recruiter."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not recruiter:
        return []

    # Get all jobs by this recruiter
    job_ids = [j.id for j in db.query(Job.id).filter(Job.recruiter_id == recruiter.id).all()]
    
    if not job_ids:
        return []

    applications = db.query(Application).filter(
        Application.job_id.in_(job_ids)
    ).order_by(Application.applied_at.desc()).all()

    result = []
    for app in applications:
        user = db.query(User).filter(User.id == app.user_id).first()
        profile = db.query(UserProfile).filter(UserProfile.user_id == app.user_id).first()
        resume = db.query(Resume).filter(Resume.id == app.resume_id).first() if app.resume_id else None
        job = db.query(Job).filter(Job.id == app.job_id).first()

        # Combine skills from profile and resume
        skills = set()
        if profile and profile.skills:
            skills.update(profile.skills)
        if resume and resume.parsed_skills:
            skills.update(resume.parsed_skills)

        result.append(ApplicationResponse(
            id=app.id,
            user_id=app.user_id,
            job_id=app.job_id,
            resume_id=app.resume_id,
            cover_letter=app.cover_letter,
            status=app.status,
            matching_score=app.matching_score,
            applied_at=app.applied_at,
            updated_at=app.updated_at,
            job_title=job.title if job else "Unknown",
            applicant_name=profile.full_name if profile else None,
            applicant_email=user.email if user else None,
            skills=list(skills),
            education=profile.education if profile else [],
            experience=profile.experience if profile else []
        ))

    return result


@router.get("/jobs/{job_id}/applicants/filter", response_model=List[ApplicationResponse])
def filter_applicants_by_skills(
    job_id: int,
    skills: str = Query(..., description="Comma-separated skills to filter by"),
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Filter applicants by skills."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    job = db.query(Job).filter(
        Job.id == job_id, Job.recruiter_id == recruiter.id
    ).first()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    required_skills = [s.strip().lower() for s in skills.split(",")]

    applications = db.query(Application).filter(
        Application.job_id == job_id
    ).all()

    filtered = []
    for app in applications:
        resume = db.query(Resume).filter(Resume.id == app.resume_id).first() if app.resume_id else None
        profile = db.query(UserProfile).filter(UserProfile.user_id == app.user_id).first()

        # Check skills from resume or profile
        user_skills = set()
        if resume and resume.parsed_skills:
            user_skills.update(s.lower() for s in resume.parsed_skills)
        if profile and profile.skills:
            user_skills.update(s.lower() for s in profile.skills)

        # Check if user has at least one required skill
        if any(skill in user_skills for skill in required_skills):
            user = db.query(User).filter(User.id == app.user_id).first()
            filtered.append(ApplicationResponse(
                id=app.id,
                user_id=app.user_id,
                job_id=app.job_id,
                resume_id=app.resume_id,
                cover_letter=app.cover_letter,
                status=app.status,
                matching_score=app.matching_score,
                applied_at=app.applied_at,
                updated_at=app.updated_at,
                job_title=job.title,
                applicant_name=profile.full_name if profile else None,
                applicant_email=user.email if user else None,
            ))

    return filtered


# --- Resume Download ---
@router.get("/applicants/{application_id}/resume/download")
def download_resume(
    application_id: int,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Download an applicant's resume."""
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify recruiter owns the job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not job or job.recruiter_id != recruiter.id:
        raise HTTPException(status_code=403, detail="Access denied")

    if not application.resume_id:
        raise HTTPException(status_code=404, detail="No resume attached to this application")

    resume = db.query(Resume).filter(Resume.id == application.resume_id).first()
    if not resume or not os.path.exists(resume.file_path):
        raise HTTPException(status_code=404, detail="Resume file not found")

    return FileResponse(
        path=resume.file_path,
        filename=resume.filename,
        media_type="application/octet-stream",
    )


# --- Change Status ---
@router.put("/applications/{application_id}/status", response_model=ApplicationResponse)
def change_application_status(
    application_id: int,
    status_update: ApplicationStatusUpdate,
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Change an application's status."""
    valid_statuses = ["applied", "shortlisted", "rejected", "interview_scheduled", "selected"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status. Must be one of: {', '.join(valid_statuses)}"
        )

    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    # Verify recruiter owns the job
    job = db.query(Job).filter(Job.id == application.job_id).first()
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not job or job.recruiter_id != recruiter.id:
        raise HTTPException(status_code=403, detail="Access denied")

    old_status = application.status
    application.status = status_update.status
    db.commit()

    # Record status history
    history = ApplicationStatusHistory(
        application_id=application.id,
        old_status=old_status,
        new_status=status_update.status,
        changed_by=current_user.id,
        notes=status_update.notes,
    )
    db.add(history)
    db.commit()

    # Notify applicant
    create_notification(
        db, application.user_id, "application_update",
        "Application Status Updated",
        f"Your application for '{job.title}' has been updated to: {status_update.status}",
        reference_id=application.id, reference_type="application",
    )

    return ApplicationResponse(
        id=application.id,
        user_id=application.user_id,
        job_id=application.job_id,
        resume_id=application.resume_id,
        cover_letter=application.cover_letter,
        status=application.status,
        matching_score=application.matching_score,
        applied_at=application.applied_at,
        updated_at=application.updated_at,
        job_title=job.title,
    )


# --- Analytics ---
@router.get("/analytics")
def recruiter_analytics(
    current_user: User = Depends(require_role("recruiter")),
    db: Session = Depends(get_db)
):
    """Get recruiter's analytics dashboard data."""
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.user_id == current_user.id
    ).first()
    if not recruiter:
        raise HTTPException(status_code=404, detail="Recruiter profile not found")

    return get_recruiter_analytics(db, recruiter.id)
