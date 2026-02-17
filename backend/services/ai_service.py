import re
import random
from typing import List, Optional
from sqlalchemy.orm import Session
from models.job import Job
from models.user import UserProfile, Resume
from models.application import Application


def get_resume_match_score(
    user_skills: List[str],
    resume_text: str,
    job: Job
) -> dict:
    """Smart Resume Matching Score - compare user skills against job requirements."""
    job_skills = job.skills_required or []
    job_desc = job.description or ""

    if not job_skills and not job_desc:
        return {
            "overall_score": 0,
            "skill_match_score": 0,
            "keyword_match_score": 0,
            "matched_skills": [],
            "missing_skills": list(job_skills),
            "recommendations": ["Add more relevant skills to your resume."],
        }

    user_skills_lower = {s.lower() for s in user_skills}
    job_skills_lower = {s.lower() for s in job_skills}

    matched = user_skills_lower.intersection(job_skills_lower)
    missing = job_skills_lower - user_skills_lower

    skill_score = (len(matched) / len(job_skills_lower) * 100) if job_skills_lower else 0

    # Keyword overlap from job description
    job_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', job_desc.lower()))
    resume_words = set(re.findall(r'\b[a-zA-Z]{3,}\b', resume_text.lower()))
    stop_words = {"the", "and", "for", "are", "but", "not", "you", "all", "can",
                  "has", "her", "was", "one", "our", "out", "with", "have", "this",
                  "will", "your", "from", "they", "been", "said", "each", "which"}
    job_words -= stop_words
    resume_words -= stop_words
    keyword_overlap = job_words.intersection(resume_words)
    keyword_score = (len(keyword_overlap) / len(job_words) * 100) if job_words else 0

    overall = skill_score * 0.7 + keyword_score * 0.3

    recommendations = []
    if missing:
        recommendations.append(f"Consider learning: {', '.join(s.title() for s in list(missing)[:5])}")
    if overall < 50:
        recommendations.append("Your resume has a low match. Try tailoring it to the job description.")
    if overall >= 70:
        recommendations.append("Great match! Make sure to highlight your relevant experience.")

    return {
        "overall_score": round(overall, 1),
        "skill_match_score": round(skill_score, 1),
        "keyword_match_score": round(keyword_score, 1),
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
        "recommendations": recommendations,
    }


def get_personalized_recommendations(
    db: Session,
    user_id: int,
    user_skills: List[str],
    limit: int = 10
) -> List[dict]:
    """Personalized Job Recommendations based on user skills and application history."""
    if not user_skills:
        # If no skills, return recent active jobs
        jobs = db.query(Job).filter(
            Job.is_approved == True, Job.is_active == True
        ).order_by(Job.created_at.desc()).limit(limit).all()
        return [
            {
                "job_id": j.id,
                "title": j.title,
                "location": j.location,
                "stipend_min": j.stipend_min,
                "stipend_max": j.stipend_max,
                "match_score": 0,
                "matched_skills": [],
                "reason": "New job posting - complete your profile skills for better matches",
            }
            for j in jobs
        ]

    # Get jobs user hasn't applied to yet
    applied_job_ids = [
        a.job_id for a in db.query(Application.job_id).filter(
            Application.user_id == user_id
        ).all()
    ]

    jobs = db.query(Job).filter(
        Job.is_approved == True,
        Job.is_active == True,
        ~Job.id.in_(applied_job_ids) if applied_job_ids else True,
    ).all()

    user_skills_lower = {s.lower() for s in user_skills}

    scored_jobs = []
    for job in jobs:
        job_skills_lower = {s.lower() for s in (job.skills_required or [])}
        if not job_skills_lower:
            continue

        matched = user_skills_lower.intersection(job_skills_lower)
        score = (len(matched) / len(job_skills_lower)) * 100

        if score > 0:
            from models.recruiter import RecruiterProfile
            recruiter = db.query(RecruiterProfile).filter(
                RecruiterProfile.id == job.recruiter_id
            ).first()

            scored_jobs.append({
                "job_id": job.id,
                "title": job.title,
                "company_name": recruiter.company_name if recruiter else None,
                "location": job.location,
                "stipend_min": job.stipend_min,
                "stipend_max": job.stipend_max,
                "match_score": round(score, 1),
                "matched_skills": [s.title() for s in matched],
                "reason": f"Matches {len(matched)} of your skills: {', '.join(s.title() for s in list(matched)[:3])}",
            })

    # Sort by match score
    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    return scored_jobs[:limit]


def get_skill_gap_analysis(
    user_skills: List[str],
    job: Job
) -> dict:
    """Skill Gap Analysis - identify missing skills and suggest learning paths."""
    job_skills = job.skills_required or []
    user_skills_lower = {s.lower() for s in user_skills}
    job_skills_lower = {s.lower() for s in job_skills}

    matched = user_skills_lower.intersection(job_skills_lower)
    missing = job_skills_lower - user_skills_lower

    gap_percentage = (len(missing) / len(job_skills_lower) * 100) if job_skills_lower else 0

    # Generate learning suggestions
    learning_resources = {
        "python": {"priority": "high", "resources": ["Python.org tutorials", "Automate the Boring Stuff", "LeetCode Python track"]},
        "java": {"priority": "high", "resources": ["Oracle Java tutorials", "Codecademy Java", "HackerRank Java"]},
        "javascript": {"priority": "high", "resources": ["MDN Web Docs", "freeCodeCamp", "JavaScript.info"]},
        "react": {"priority": "high", "resources": ["React official docs", "Scrimba React course", "Build projects on Frontend Mentor"]},
        "angular": {"priority": "medium", "resources": ["Angular.io docs", "Tour of Heroes tutorial", "Udemy Angular courses"]},
        "django": {"priority": "medium", "resources": ["Django official tutorial", "Django for Beginners book", "Django REST framework docs"]},
        "flask": {"priority": "medium", "resources": ["Flask Mega-Tutorial", "Flask official docs", "Build REST APIs with Flask"]},
        "sql": {"priority": "high", "resources": ["SQLZoo", "Mode Analytics SQL tutorial", "LeetCode Database problems"]},
        "machine learning": {"priority": "high", "resources": ["Andrew Ng's ML course", "Kaggle Learn", "Hands-On ML book"]},
        "docker": {"priority": "medium", "resources": ["Docker official docs", "Play with Docker", "Docker for beginners"]},
        "git": {"priority": "high", "resources": ["Git official docs", "Atlassian Git tutorials", "Learn Git Branching"]},
        "aws": {"priority": "medium", "resources": ["AWS Free Tier", "AWS Skill Builder", "A Cloud Guru"]},
        "data science": {"priority": "high", "resources": ["DataCamp", "Kaggle", "Google Data Analytics Certificate"]},
    }

    suggestions = []
    for skill in missing:
        skill_lower = skill.lower()
        if skill_lower in learning_resources:
            info = learning_resources[skill_lower]
            suggestions.append({
                "skill": skill.title(),
                "priority": info["priority"],
                "resources": info["resources"],
            })
        else:
            suggestions.append({
                "skill": skill.title(),
                "priority": "medium",
                "resources": [
                    f"Search for '{skill}' on Coursera",
                    f"YouTube tutorials on {skill}",
                    f"Practice {skill} on relevant platforms",
                ],
            })

    # Sort by priority
    priority_order = {"high": 0, "medium": 1, "low": 2}
    suggestions.sort(key=lambda x: priority_order.get(x["priority"], 1))

    return {
        "user_skills": [s.title() for s in user_skills_lower],
        "required_skills": [s.title() for s in job_skills_lower],
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
        "gap_percentage": round(gap_percentage, 1),
        "learning_suggestions": suggestions,
    }


def generate_interview_prep(job: Job, user_skills: List[str]) -> dict:
    """AI-Powered Interview Preparation - generate questions and tips."""
    job_title = job.title or "Software Engineer"
    job_skills = job.skills_required or []
    job_desc = job.description or ""

    # Technical questions based on required skills
    skill_questions = {
        "python": [
            {"question": "What are Python decorators and how do they work?", "difficulty": "medium",
             "sample_answer": "Decorators are functions that modify the behavior of other functions. They use the @decorator syntax and wrap functions to add functionality."},
            {"question": "Explain the difference between lists and tuples in Python.", "difficulty": "easy",
             "sample_answer": "Lists are mutable (can be changed after creation), tuples are immutable. Tuples are slightly faster and can be used as dictionary keys."},
        ],
        "javascript": [
            {"question": "What is the difference between var, let, and const?", "difficulty": "easy",
             "sample_answer": "var has function scope, let and const have block scope. const cannot be reassigned. var is hoisted, let/const are in temporal dead zone."},
            {"question": "Explain closures in JavaScript.", "difficulty": "medium",
             "sample_answer": "A closure is a function that has access to variables in its outer scope, even after the outer function has returned."},
        ],
        "react": [
            {"question": "What are React hooks and why were they introduced?", "difficulty": "medium",
             "sample_answer": "Hooks let you use state and lifecycle features in functional components. They were introduced to simplify component logic and enable code reuse."},
            {"question": "Explain the virtual DOM in React.", "difficulty": "easy",
             "sample_answer": "The virtual DOM is a lightweight copy of the actual DOM. React uses it to determine what changes need to be made, then updates only the changed parts."},
        ],
        "sql": [
            {"question": "What is the difference between INNER JOIN and LEFT JOIN?", "difficulty": "easy",
             "sample_answer": "INNER JOIN returns only matching rows from both tables. LEFT JOIN returns all rows from the left table and matching rows from the right."},
            {"question": "How do you optimize a slow SQL query?", "difficulty": "hard",
             "sample_answer": "Use indexes, avoid SELECT *, use EXPLAIN to analyze query plan, optimize JOINs, avoid subqueries when possible, use pagination."},
        ],
        "machine learning": [
            {"question": "What is overfitting and how do you prevent it?", "difficulty": "medium",
             "sample_answer": "Overfitting is when a model performs well on training data but poorly on new data. Prevention: regularization, cross-validation, more data, simpler models."},
        ],
    }

    # Behavioral questions
    behavioral_questions = [
        {"question": "Tell me about a challenging project you worked on.", "difficulty": "medium",
         "sample_answer": "Structure your answer using STAR method: Situation, Task, Action, Result. Focus on your specific contributions."},
        {"question": "How do you handle tight deadlines?", "difficulty": "easy",
         "sample_answer": "Prioritize tasks, communicate early about blockers, break work into smaller chunks, and focus on delivering the most valuable features first."},
        {"question": "Describe a time you disagreed with a team member.", "difficulty": "medium",
         "sample_answer": "Focus on how you communicated professionally, listened to their perspective, and found a compromise or solution."},
        {"question": f"Why are you interested in this {job_title} position?", "difficulty": "easy",
         "sample_answer": "Research the company, align your skills with the role, and show genuine enthusiasm for the industry/technology."},
    ]

    # Collect relevant technical questions
    questions = []
    for skill in job_skills:
        skill_lower = skill.lower()
        if skill_lower in skill_questions:
            for q in skill_questions[skill_lower]:
                q_copy = q.copy()
                q_copy["category"] = "technical"
                questions.append(q_copy)

    # Add behavioral questions
    for q in behavioral_questions:
        q_copy = q.copy()
        q_copy["category"] = "behavioral"
        questions.append(q_copy)

    # Generate tips
    tips = [
        f"Research the company thoroughly before the interview.",
        f"Review the job description and prepare examples for each requirement.",
        f"Practice coding problems related to: {', '.join(job_skills[:5]) if job_skills else 'general programming'}.",
        "Prepare 2-3 questions to ask the interviewer about the team and projects.",
        "Use the STAR method (Situation, Task, Action, Result) for behavioral questions.",
        "Test your audio/video setup before a virtual interview.",
        "Be ready to discuss your resume and past projects in detail.",
    ]

    # Focus areas
    focus_areas = list(set(job_skills[:6])) if job_skills else ["Problem Solving", "Communication"]
    focus_areas.append("System Design" if "senior" in job_title.lower() else "Coding Fundamentals")

    return {
        "questions": questions,
        "tips": tips,
        "focus_areas": focus_areas,
        "company_research_points": [
            "Company mission and values",
            "Recent news and product launches",
            "Tech stack and engineering blog",
            "Company culture and team structure",
            "Growth plans and industry position",
        ],
    }
