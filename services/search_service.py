from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, func
from typing import List, Optional
from models.job import Job
from models.recruiter import RecruiterProfile


def search_jobs(
    db: Session,
    query: Optional[str] = None,
    location: Optional[str] = None,
    skills: Optional[List[str]] = None,
    stipend_min: Optional[float] = None,
    stipend_max: Optional[float] = None,
    job_type: Optional[str] = None,
    is_remote: Optional[bool] = None,
    sort_by: str = "created_at",
    page: int = 1,
    page_size: int = 20,
) -> dict:
    """Advanced job search with filters, sorting, and pagination."""

    base_query = db.query(Job).filter(
        Job.is_approved == True,
        Job.is_active == True
    )

    # Text search in title and description
    if query:
        search_term = f"%{query}%"
        base_query = base_query.filter(
            or_(
                Job.title.ilike(search_term),
                Job.description.ilike(search_term),
            )
        )

    # Location filter
    if location:
        base_query = base_query.filter(Job.location.ilike(f"%{location}%"))

    # Skills filter - check if any required skill matches
    if skills:
        skill_filters = []
        for skill in skills:
            skill_filters.append(
                func.lower(func.cast(Job.skills_required, db.bind.dialect.name == 'sqlite' and 'TEXT' or 'VARCHAR')).contains(skill.lower())
            )
        if skill_filters:
            base_query = base_query.filter(or_(*skill_filters))

    # Stipend range filter
    if stipend_min is not None:
        base_query = base_query.filter(
            or_(Job.stipend_max >= stipend_min, Job.stipend_max.is_(None))
        )
    if stipend_max is not None:
        base_query = base_query.filter(
            or_(Job.stipend_min <= stipend_max, Job.stipend_min.is_(None))
        )

    # Job type filter
    if job_type:
        base_query = base_query.filter(Job.job_type == job_type)

    # Remote filter
    if is_remote is not None:
        base_query = base_query.filter(Job.is_remote == is_remote)

    # Get total count before pagination
    total_count = base_query.count()

    # Sorting
    if sort_by == "stipend":
        base_query = base_query.order_by(Job.stipend_max.desc().nullslast())
    elif sort_by == "views":
        base_query = base_query.order_by(Job.views_count.desc())
    else:  # default: created_at
        base_query = base_query.order_by(Job.created_at.desc())

    # Pagination
    offset = (page - 1) * page_size
    jobs = base_query.offset(offset).limit(page_size).all()

    return {
        "jobs": jobs,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
    }
