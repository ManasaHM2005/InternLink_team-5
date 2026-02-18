from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime
from database import get_db
from models.user import User, UserProfile
from models.job import Job
from models.recruiter import RecruiterProfile
from models.dispute import Dispute
from schemas.admin_schemas import AdminUserUpdate, AdminJobApproval, DisputeCreate, DisputeUpdate, DisputeResponse, PlatformAnalytics
from schemas.user_schemas import UserResponse
from schemas.job_schemas import JobResponse
from utils.dependencies import get_current_user, require_role
from services.analytics_service import get_platform_analytics
from services.notification_service import create_notification

router = APIRouter(prefix="/admin", tags=["Admin"])


# --- User Management ---
@router.get("/users", response_model=List[UserResponse])
def list_users(
    role: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all users with optional filters."""
    query = db.query(User)

    if role:
        query = query.filter(User.role == role)
    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.offset((page - 1) * page_size).limit(page_size).all()

    return users


@router.put("/users/{user_id}")
def update_user(
    user_id: int,
    user_update: AdminUserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update or deactivate a user."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_update.is_active is not None:
        user.is_active = user_update.is_active
    if user_update.role is not None:
        user.role = user_update.role

    db.commit()
    db.refresh(user)

    return {"message": "User updated successfully", "user_id": user_id}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Deactivate a user account."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = False
    db.commit()

    return {"message": "User deactivated successfully"}


# --- Recruiter Management ---
@router.get("/recruiters")
def list_recruiters(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all recruiters with their company profiles."""
    recruiters = db.query(User).filter(User.role == "recruiter").all()
    result = []
    for r in recruiters:
        profile = db.query(RecruiterProfile).filter(
            RecruiterProfile.user_id == r.id
        ).first()
        result.append({
            "id": r.id,
            "email": r.email,
            "is_active": r.is_active,
            "created_at": r.created_at.isoformat(),
            "company_name": profile.company_name if profile else None,
            "industry": profile.industry if profile else None,
        })
    return result


@router.put("/recruiters/{user_id}")
def update_recruiter(
    user_id: int,
    user_update: AdminUserUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Update or deactivate a recruiter."""
    user = db.query(User).filter(User.id == user_id, User.role == "recruiter").first()
    if not user:
        raise HTTPException(status_code=404, detail="Recruiter not found")

    if user_update.is_active is not None:
        user.is_active = user_update.is_active

    db.commit()
    return {"message": "Recruiter updated successfully"}


# --- Job Approval ---
@router.get("/jobs/pending", response_model=List[JobResponse])
def get_pending_jobs(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get jobs pending approval."""
    jobs = db.query(Job).filter(Job.is_approved == False).order_by(Job.created_at.desc()).all()
    result = []
    for job in jobs:
        recruiter = db.query(RecruiterProfile).filter(
            RecruiterProfile.id == job.recruiter_id
        ).first()
        result.append(JobResponse(
            **{c.name: getattr(job, c.name) for c in job.__table__.columns},
            company_name=recruiter.company_name if recruiter else None,
        ))
    return result


@router.put("/jobs/{job_id}/approve")
def approve_or_reject_job(
    job_id: int,
    approval: AdminJobApproval,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Approve or reject a job posting."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.is_approved = approval.is_approved
    db.commit()

    # Notify recruiter
    recruiter = db.query(RecruiterProfile).filter(
        RecruiterProfile.id == job.recruiter_id
    ).first()
    if recruiter:
        status_text = "approved" if approval.is_approved else "rejected"
        create_notification(
            db, recruiter.user_id, "job_approved",
            f"Job {status_text.title()}",
            f"Your job posting '{job.title}' has been {status_text}." + (f" Notes: {approval.notes}" if approval.notes else ""),
            reference_id=job.id, reference_type="job",
        )

    return {
        "message": f"Job {'approved' if approval.is_approved else 'rejected'} successfully",
        "job_id": job_id,
    }


# --- Analytics ---
@router.get("/analytics", response_model=PlatformAnalytics)
def platform_analytics(
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Get platform-wide analytics."""
    return get_platform_analytics(db)


# --- Disputes ---
@router.get("/disputes", response_model=List[DisputeResponse])
def list_disputes(
    status_filter: Optional[str] = Query(None, alias="status"),
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """List all disputes."""
    query = db.query(Dispute)
    if status_filter:
        query = query.filter(Dispute.status == status_filter)
    disputes = query.order_by(Dispute.created_at.desc()).all()
    return disputes


@router.put("/disputes/{dispute_id}", response_model=DisputeResponse)
def update_dispute(
    dispute_id: int,
    dispute_update: DisputeUpdate,
    current_user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db)
):
    """Resolve or update a dispute."""
    dispute = db.query(Dispute).filter(Dispute.id == dispute_id).first()
    if not dispute:
        raise HTTPException(status_code=404, detail="Dispute not found")

    dispute.status = dispute_update.status
    if dispute_update.admin_notes:
        dispute.admin_notes = dispute_update.admin_notes
    if dispute_update.resolution:
        dispute.resolution = dispute_update.resolution
    if dispute_update.status in ["resolved", "dismissed"]:
        dispute.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(dispute)

    # Notify the user who filed the dispute
    create_notification(
        db, dispute.filed_by, "dispute_update",
        "Dispute Updated",
        f"Your dispute '{dispute.subject}' status: {dispute.status}",
        reference_id=dispute.id, reference_type="dispute",
    )

    return dispute


# --- File a Dispute (available to any authenticated user) ---
@router.post("/disputes", response_model=DisputeResponse, status_code=status.HTTP_201_CREATED)
def file_dispute(
    dispute_data: DisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """File a new dispute."""
    dispute = Dispute(
        filed_by=current_user.id,
        against_user=dispute_data.against_user,
        job_id=dispute_data.job_id,
        subject=dispute_data.subject,
        description=dispute_data.description,
    )
    db.add(dispute)
    db.commit()
    db.refresh(dispute)
    return dispute
