from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from models.user import User, UserProfile, Resume
from models.job import Job
from models.recruiter import RecruiterProfile
from models.interview import InterviewPrep
from schemas.ai_schemas import ResumeMatchResponse, JobRecommendation, SkillGapResponse, InterviewPrepResponse
from utils.dependencies import get_current_user
from services.ai_service import get_resume_match_score, get_personalized_recommendations, get_skill_gap_analysis, generate_interview_prep
from typing import List

router = APIRouter(prefix="/ai", tags=["AI Features"])


def _get_user_skills(db: Session, user_id: int) -> tuple:
    """Get user skills from profile and resume."""
    profile = db.query(UserProfile).filter(UserProfile.user_id == user_id).first()
    resume = db.query(Resume).filter(Resume.user_id == user_id, Resume.is_primary == True).first()
    skills = set()
    if profile and profile.skills:
        skills.update(profile.skills)
    if resume and resume.parsed_skills:
        skills.update(resume.parsed_skills)
    resume_text = resume.parsed_text if resume and resume.parsed_text else ""
    return list(skills), resume_text


@router.get("/resume-match/{job_id}", response_model=ResumeMatchResponse)
def smart_resume_match(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get smart resume matching score for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    skills, resume_text = _get_user_skills(db, current_user.id)
    result = get_resume_match_score(skills, resume_text, job)

    return ResumeMatchResponse(
        job_id=job.id, job_title=job.title,
        overall_score=result["overall_score"],
        skill_match_score=result["skill_match_score"],
        keyword_match_score=result["keyword_match_score"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        recommendations=result["recommendations"],
    )


@router.get("/recommendations", response_model=List[JobRecommendation])
def get_recommendations(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get personalized job recommendations."""
    skills, _ = _get_user_skills(db, current_user.id)
    recommendations = get_personalized_recommendations(db, current_user.id, skills)
    return [JobRecommendation(**r) for r in recommendations]


@router.get("/skill-gap/{job_id}", response_model=SkillGapResponse)
def skill_gap_analysis(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get skill gap analysis for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    skills, _ = _get_user_skills(db, current_user.id)
    result = get_skill_gap_analysis(skills, job)

    return SkillGapResponse(
        job_id=job.id, job_title=job.title,
        user_skills=result["user_skills"],
        required_skills=result["required_skills"],
        matched_skills=result["matched_skills"],
        missing_skills=result["missing_skills"],
        gap_percentage=result["gap_percentage"],
        learning_suggestions=result["learning_suggestions"],
    )


@router.get("/interview-prep/{job_id}", response_model=InterviewPrepResponse)
def interview_preparation(job_id: int, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Get AI-powered interview preparation for a job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    skills, _ = _get_user_skills(db, current_user.id)
    result = generate_interview_prep(job, skills)

    # Save prep for user
    prep = InterviewPrep(
        user_id=current_user.id, job_id=job.id,
        questions=result["questions"], tips=result["tips"],
        focus_areas=result["focus_areas"],
    )
    db.add(prep)
    db.commit()

    recruiter = db.query(RecruiterProfile).filter(RecruiterProfile.id == job.recruiter_id).first()

    return InterviewPrepResponse(
        job_id=job.id, job_title=job.title,
        questions=result["questions"], tips=result["tips"],
        focus_areas=result["focus_areas"],
        company_research_points=result["company_research_points"],
    )
@router.post("/interview-chat/{job_id}")
def interview_chat(job_id: int, message_data: dict, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Handle chat interaction for interview prep."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    message = message_data.get("message", "").lower()
    
    # Simple logic for practice
    if "practice" in message or "start" in message:
        return {"response": "Great! Let's start. Here is your first question: **Tell me about a time you faced a difficult technical challenge and how you solved it.**"}
    
    if "star" in message:
        return {"response": "Exactly! The **STAR** method (Situation, Task, Action, Result) is the best way to structure your answers."}

    responses = [
        "That's a good point. How would you apply that to a real-world project?",
        "Can you elaborate on the technical aspects of that?",
        "Interesting! What was the most challenging part of that experience?",
        "How do you usually handle disagreements with team members during such projects?",
        "That sounds like a solid approach. Let's move to a technical question. How do you ensure your code is scalable?"
    ]
    return {"response": random.choice(responses)}
