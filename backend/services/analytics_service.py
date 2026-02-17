from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from datetime import datetime, timedelta
from models.user import User, UserProfile
from models.job import Job
from models.application import Application
from models.dispute import Dispute
from models.recruiter import RecruiterProfile


def get_recruiter_analytics(db: Session, recruiter_id: int) -> dict:
    """Get analytics for a recruiter's dashboard."""
    # Get all jobs for this recruiter
    jobs = db.query(Job).filter(Job.recruiter_id == recruiter_id).all()
    job_ids = [j.id for j in jobs]

    if not job_ids:
        return {
            "total_jobs": 0,
            "active_jobs": 0,
            "total_applications": 0,
            "total_views": 0,
            "avg_applications_per_job": 0,
            "status_breakdown": {},
            "jobs_analytics": [],
        }

    total_applications = db.query(Application).filter(
        Application.job_id.in_(job_ids)
    ).count()

    total_views = sum(j.views_count for j in jobs)

    # Status breakdown
    status_counts = db.query(
        Application.status, func.count(Application.id)
    ).filter(
        Application.job_id.in_(job_ids)
    ).group_by(Application.status).all()

    status_breakdown = {status: count for status, count in status_counts}

    # Per-job analytics
    jobs_analytics = []
    for job in jobs:
        app_count = db.query(Application).filter(Application.job_id == job.id).count()
        jobs_analytics.append({
            "job_id": job.id,
            "title": job.title,
            "applications": app_count,
            "views": job.views_count,
            "conversion_rate": round((app_count / job.views_count * 100), 1) if job.views_count > 0 else 0,
            "is_active": job.is_active,
            "created_at": job.created_at.isoformat(),
        })

    return {
        "total_jobs": len(jobs),
        "active_jobs": sum(1 for j in jobs if j.is_active),
        "total_applications": total_applications,
        "total_views": total_views,
        "avg_applications_per_job": round(total_applications / len(jobs), 1) if jobs else 0,
        "status_breakdown": status_breakdown,
        "jobs_analytics": jobs_analytics,
    }


def get_platform_analytics(db: Session) -> dict:
    """Get platform-wide analytics for admin dashboard."""
    now = datetime.utcnow()
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    total_users = db.query(User).filter(User.role == "user").count()
    total_recruiters = db.query(User).filter(User.role == "recruiter").count()
    total_jobs = db.query(Job).count()
    total_applications = db.query(Application).count()
    active_jobs = db.query(Job).filter(Job.is_active == True, Job.is_approved == True).count()
    pending_approvals = db.query(Job).filter(Job.is_approved == False).count()
    total_disputes = db.query(Dispute).count()
    open_disputes = db.query(Dispute).filter(Dispute.status.in_(["open", "under_review"])).count()

    # This month stats
    users_this_month = db.query(User).filter(
        User.created_at >= month_start, User.role == "user"
    ).count()
    jobs_this_month = db.query(Job).filter(Job.created_at >= month_start).count()
    applications_this_month = db.query(Application).filter(
        Application.applied_at >= month_start
    ).count()

    # Top skills from job postings
    all_jobs = db.query(Job).filter(Job.is_approved == True).all()
    skill_counts = {}
    for job in all_jobs:
        for skill in (job.skills_required or []):
            skill_lower = skill.lower()
            skill_counts[skill_lower] = skill_counts.get(skill_lower, 0) + 1
    top_skills = sorted(skill_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    top_skills = [{"skill": s.title(), "count": c} for s, c in top_skills]

    # Application status breakdown
    status_counts = db.query(
        Application.status, func.count(Application.id)
    ).group_by(Application.status).all()
    application_status_breakdown = {status: count for status, count in status_counts}

    return {
        "total_users": total_users,
        "total_recruiters": total_recruiters,
        "total_jobs": total_jobs,
        "total_applications": total_applications,
        "active_jobs": active_jobs,
        "pending_approvals": pending_approvals,
        "total_disputes": total_disputes,
        "open_disputes": open_disputes,
        "users_this_month": users_this_month,
        "jobs_this_month": jobs_this_month,
        "applications_this_month": applications_this_month,
        "top_skills": top_skills,
        "application_status_breakdown": application_status_breakdown,
    }
