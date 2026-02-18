import os
import re
from typing import List, Optional
from config import settings


def save_resume(file_content: bytes, filename: str, user_id: int) -> str:
    """Save a resume file and return the file path."""
    safe_filename = f"user_{user_id}_{filename}"
    file_path = os.path.join(settings.UPLOAD_DIR, "resumes", safe_filename)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


def delete_resume(file_path: str):
    """Delete a resume file."""
    if os.path.exists(file_path):
        os.remove(file_path)


def parse_resume_text(file_path: str) -> str:
    """Extract text from a resume file (basic implementation)."""
    try:
        # For .txt files, read directly
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # For PDF/DOC - return file info (in production, use pdfminer/docx2txt)
        with open(file_path, "rb") as f:
            content = f.read()
            # Basic text extraction attempt
            try:
                text = content.decode("utf-8", errors="ignore")
                # Clean up non-printable characters
                text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
                return text.strip()
            except Exception:
                return ""
    except Exception:
        return ""


def extract_skills_from_text(text: str) -> List[str]:
    """Extract skills from resume text using keyword matching."""
    # Comprehensive skill keywords
    skill_keywords = [
        # Programming Languages
        "python", "java", "javascript", "typescript", "c++", "c#", "ruby", "go",
        "rust", "swift", "kotlin", "php", "scala", "r", "matlab", "perl",
        # Web Frameworks
        "react", "angular", "vue", "django", "flask", "fastapi", "express",
        "spring", "rails", "laravel", "next.js", "nuxt.js", "svelte",
        # Data & AI
        "machine learning", "deep learning", "tensorflow", "pytorch", "pandas",
        "numpy", "scikit-learn", "nlp", "computer vision", "data science",
        "data analysis", "big data", "spark", "hadoop",
        # Databases
        "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
        "cassandra", "dynamodb", "firebase", "sqlite",
        # Cloud & DevOps
        "aws", "azure", "gcp", "docker", "kubernetes", "terraform", "jenkins",
        "ci/cd", "linux", "git", "github", "gitlab",
        # Mobile
        "android", "ios", "react native", "flutter", "xamarin",
        # Design
        "figma", "sketch", "adobe xd", "photoshop", "illustrator",
        # Other
        "html", "css", "rest api", "graphql", "microservices", "agile",
        "scrum", "jira", "confluence", "tableau", "power bi",
        "excel", "communication", "leadership", "teamwork", "problem solving",
    ]

    text_lower = text.lower()
    found_skills = []

    for skill in skill_keywords:
        if skill in text_lower:
            found_skills.append(skill.title() if len(skill) > 3 else skill.upper())

    return list(set(found_skills))


def calculate_resume_match_score(
    resume_skills: List[str],
    job_skills: List[str],
    resume_text: str,
    job_description: str
) -> dict:
    """Calculate a matching score between a resume and job posting."""
    if not job_skills:
        return {
            "overall_score": 0,
            "skill_match_score": 0,
            "keyword_match_score": 0,
            "matched_skills": [],
            "missing_skills": [],
        }

    # Normalize skills for comparison
    resume_skills_lower = {s.lower() for s in resume_skills}
    job_skills_lower = {s.lower() for s in job_skills}

    # Skill match score
    matched = resume_skills_lower.intersection(job_skills_lower)
    missing = job_skills_lower - resume_skills_lower
    skill_match_score = (len(matched) / len(job_skills_lower)) * 100 if job_skills_lower else 0

    # Keyword match score (from job description in resume text)
    job_words = set(re.findall(r'\b\w+\b', job_description.lower()))
    resume_words = set(re.findall(r'\b\w+\b', resume_text.lower()))
    # Remove common stop words
    stop_words = {"the", "a", "an", "is", "are", "was", "were", "be", "been",
                  "being", "have", "has", "had", "do", "does", "did", "will",
                  "would", "could", "should", "may", "might", "and", "or", "but",
                  "in", "on", "at", "to", "for", "of", "with", "by", "from"}
    job_words -= stop_words
    resume_words -= stop_words
    keyword_overlap = job_words.intersection(resume_words)
    keyword_match_score = (len(keyword_overlap) / len(job_words)) * 100 if job_words else 0

    # Overall score (weighted average)
    overall_score = (skill_match_score * 0.7) + (keyword_match_score * 0.3)

    return {
        "overall_score": round(overall_score, 1),
        "skill_match_score": round(skill_match_score, 1),
        "keyword_match_score": round(keyword_match_score, 1),
        "matched_skills": [s.title() for s in matched],
        "missing_skills": [s.title() for s in missing],
    }
