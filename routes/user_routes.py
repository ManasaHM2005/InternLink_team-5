from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from database import get_db
from models.user import User, UserProfile, Resume
from models.job import Job
from models.application import Application, ApplicationStatusHistory
from models.recruiter import RecruiterProfile
from schemas.user_schemas import UserProfileCreate, UserProfileUpdate, UserProfileResponse, UserResponse, ResumeResponse
from schemas.application_schemas import ApplicationCreate, ApplicationResponse, ApplicationTrackingResponse, StatusHistoryResponse
from utils.dependencies import get_current_user, require_role
from services.resume_service import (
    save_resume, 
    extract_skills_from_text, 
    parse_resume_text, 
    extract_education_from_text, 
    extract_experience_from_text
)
from services.search_service import search_jobs
from services.notification_service import create_notification
import os

router = APIRouter(prefix="/users", tags=["Users"])


# --- Profile ---
@router.get("/profile", response_model=UserResponse)
def get_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get current user's profile."""
    return current_user


@router.put("/profile", response_model=UserProfileResponse)
def update_profile(
    profile_data: UserProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update current user's profile."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()

    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)

    update_data = profile_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profile, key, value)

    db.commit()
    db.refresh(profile)
    return profile


# --- Resume ---
@router.post("/resume/upload", response_model=ResumeResponse)
async def upload_resume(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Upload a resume file."""
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    allowed = [".pdf", ".doc", ".docx", ".txt"]
    if ext not in allowed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed: {', '.join(allowed)}"
        )

    # Read file content
    content = await file.read()

    # Save file
    file_path = save_resume(content, file.filename, current_user.id)

    # Parse resume for skills, education, and experience
    parsed_text = parse_resume_text(file_path)
    parsed_skills = extract_skills_from_text(parsed_text)
    extracted_edu = extract_education_from_text(parsed_text)
    extracted_exp = extract_experience_from_text(parsed_text)

    # Set existing resumes as non-primary
    db.query(Resume).filter(
        Resume.user_id == current_user.id
    ).update({"is_primary": False})

    # Create resume record
    resume = Resume(
        user_id=current_user.id,
        filename=file.filename,
        file_path=file_path,
        file_size=len(content),
        parsed_skills=parsed_skills,
        parsed_text=parsed_text,
        is_primary=True,
    )
    db.add(resume)
    
    # Update user profile automatically from resume
    profile = db.query(UserProfile).filter(UserProfile.user_id == current_user.id).first()
    if not profile:
        profile = UserProfile(user_id=current_user.id)
        db.add(profile)
        
    # Update skills
    existing_skills = [s.lower() for s in (profile.skills or [])]
    new_skills = [s for s in parsed_skills if s.lower() not in existing_skills]
    profile.skills = (profile.skills or []) + new_skills
    
    # Update education if profile current list is empty
    if not profile.education and extracted_edu:
        profile.education = extracted_edu
        
    # Update experience if profile current list is empty
    if not profile.experience and extracted_exp:
        profile.experience = extracted_exp
        
    db.commit()
    db.refresh(resume)

    return resume



@router.get("/resume", response_model=List[ResumeResponse])
def get_resumes(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get all resumes of the current user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return resumes


# --- Job Search ---
@router.get("/jobs/search")
def search_jobs_endpoint(
    query: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    skills: Optional[str] = Query(None, description="Comma-separated skills"),
    stipend_min: Optional[float] = Query(None),
    stipend_max: Optional[float] = Query(None),
    job_type: Optional[str] = Query(None),
    is_remote: Optional[bool] = Query(None),
    sort_by: str = Query("created_at"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    """Search for jobs with filters."""
    skill_list = [s.strip() for s in skills.split(",")] if skills else None

    result = search_jobs(
        db=db,
        query=query,
        location=location,
        skills=skill_list,
        stipend_min=stipend_min,
        stipend_max=stipend_max,
        job_type=job_type,
        is_remote=is_remote,
        sort_by=sort_by,
        page=page,
        page_size=page_size,
    )

    # Enrich jobs with company name
    jobs_data = []
    for job in result["jobs"]:
        recruiter = db.query(RecruiterProfile).filter(
            RecruiterProfile.id == job.recruiter_id
        ).first()
        job_dict = {
            "id": job.id,
            "title": job.title,
            "description": job.description,
            "requirements": job.requirements,
            "skills_required": job.skills_required,
            "location": job.location,
            "is_remote": job.is_remote,
            "stipend_min": job.stipend_min,
            "stipend_max": job.stipend_max,
            "job_type": job.job_type,
            "duration": job.duration,
            "openings": job.openings,
            "deadline": job.deadline.isoformat() if job.deadline else None,
            "created_at": job.created_at.isoformat(),
            "company_name": recruiter.company_name if recruiter else None,
        }
        jobs_data.append(job_dict)

    return {
        "jobs": jobs_data,
        "total_count": result["total_count"],
        "page": result["page"],
        "page_size": result["page_size"],
        "total_pages": result["total_pages"],
    }


# --- Apply ---
@router.post("/jobs/{job_id}/apply", response_model=ApplicationResponse)
def apply_to_job(
    job_id: int,
    application_data: ApplicationCreate,
    current_user: User = Depends(require_role("user")),
    db: Session = Depends(get_db)
):
    """Apply to a job/internship."""
    # Check job exists and is active
    job = db.query(Job).filter(
        Job.id == job_id, Job.is_approved == True, Job.is_active == True
    ).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found or not active")

    # Check if already applied
    existing = db.query(Application).filter(
        Application.user_id == current_user.id,
        Application.job_id == job_id,
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="You have already applied to this job")

    # Calculate matching score
    matching_score = None
    resume = None
    if application_data.resume_id:
        resume = db.query(Resume).filter(
            Resume.id == application_data.resume_id,
            Resume.user_id == current_user.id
        ).first()
    else:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id, Resume.is_primary == True
        ).first()

    if resume and resume.parsed_skills:
        from services.resume_service import calculate_resume_match_score
        match_result = calculate_resume_match_score(
            resume.parsed_skills, job.skills_required or [],
            resume.parsed_text or "", job.description or ""
        )
        matching_score = match_result["overall_score"]

    application = Application(
        user_id=current_user.id,
        job_id=job_id,
        resume_id=resume.id if resume else None,
        cover_letter=application_data.cover_letter,
        matching_score=matching_score,
    )
    db.add(application)
    db.commit()
    db.refresh(application)

    # Create initial status history
    history = ApplicationStatusHistory(
        application_id=application.id,
        new_status="applied",
        changed_by=current_user.id,
        notes="Application submitted",
    )
    db.add(history)
    db.commit()

    # Notify recruiter
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.id == job.recruiter_id
    ).first()
    if recruiter:
        create_notification(
            db, recruiter.user_id, "new_applicant",
            "New Application",
            f"New application received for '{job.title}'",
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
        company_name=recruiter.company_name if recruiter else None,
    )


# --- Applications Tracking ---
@router.get("/applications", response_model=List[ApplicationResponse])
def get_my_applications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all applications of the current user."""
    applications = db.query(Application).filter(
        Application.user_id == current_user.id
    ).order_by(Application.applied_at.desc()).all()

    result = []
    for app in applications:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        recruiter = db.query(RecruiterProfile).filter(
            RecruiterProfile.id == job.recruiter_id
        ).first() if job else None

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
            job_title=job.title if job else None,
            company_name=recruiter.company_name if recruiter else None,
        ))

    return result


@router.get("/applications/{application_id}/track", response_model=ApplicationTrackingResponse)
def track_application(
    application_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Track application status with full history."""
    application = db.query(Application).filter(
        Application.id == application_id,
        Application.user_id == current_user.id,
    ).first()
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    job = db.query(Job).filter(Job.id == application.job_id).first()
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.id == job.recruiter_id
    ).first() if job else None

    history = db.query(ApplicationStatusHistory).filter(
        ApplicationStatusHistory.application_id == application_id
    ).order_by(ApplicationStatusHistory.changed_at.asc()).all()

    interviews = []
    from models.interview import Interview
    interview_records = db.query(Interview).filter(
        Interview.application_id == application_id
    ).all()
    for i in interview_records:
        interviews.append({
            "id": i.id,
            "scheduled_at": i.scheduled_at.isoformat(),
            "duration_minutes": i.duration_minutes,
            "status": i.status,
            "meeting_url": i.meeting_url,
        })

    return ApplicationTrackingResponse(
        application=ApplicationResponse(
            id=application.id,
            user_id=application.user_id,
            job_id=application.job_id,
            resume_id=application.resume_id,
            cover_letter=application.cover_letter,
            status=application.status,
            matching_score=application.matching_score,
            applied_at=application.applied_at,
            updated_at=application.updated_at,
            job_title=job.title if job else None,
            company_name=recruiter.company_name if recruiter else None,
        ),
        status_history=[StatusHistoryResponse(
            id=h.id,
            application_id=h.application_id,
            old_status=h.old_status,
            new_status=h.new_status,
            notes=h.notes,
            changed_at=h.changed_at,
        ) for h in history],
        interviews=interviews,
    )
