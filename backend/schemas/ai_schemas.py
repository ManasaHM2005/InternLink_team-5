from pydantic import BaseModel
from typing import Optional, List


class ResumeMatchResponse(BaseModel):
    job_id: int
    job_title: str
    overall_score: float  # 0-100
    skill_match_score: float
    keyword_match_score: float
    matched_skills: List[str]
    missing_skills: List[str]
    recommendations: List[str]


class JobRecommendation(BaseModel):
    job_id: int
    title: str
    company_name: Optional[str]
    location: Optional[str]
    stipend_min: Optional[float]
    stipend_max: Optional[float]
    match_score: float
    matched_skills: List[str]
    reason: str


class SkillGapResponse(BaseModel):
    job_id: int
    job_title: str
    user_skills: List[str]
    required_skills: List[str]
    matched_skills: List[str]
    missing_skills: List[str]
    gap_percentage: float
    learning_suggestions: List[dict]
    # [{"skill": "...", "priority": "high/medium/low", "resources": ["..."]}]


class InterviewPrepResponse(BaseModel):
    job_id: int
    job_title: str
    questions: List[dict]
    # [{"question": "...", "category": "technical/behavioral", "difficulty": "easy/medium/hard", "sample_answer": "..."}]
    tips: List[str]
    focus_areas: List[str]
    company_research_points: List[str]
