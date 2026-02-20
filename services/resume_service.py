import os
import re
import PyPDF2

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
    """Extract text from a resume file."""
    try:
        # For .txt files, read directly
        if file_path.endswith(".txt"):
            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # For PDF files, use PyPDF2
        if file_path.endswith(".pdf"):
            text = ""
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()

        # For DOC/DOCX or others - return empty or basic attempt
        # (In production, consider using python-docx for .docx)
        with open(file_path, "rb") as f:
            content = f.read()
            try:
                text = content.decode("utf-8", errors="ignore")
                # Clean up non-printable characters
                text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)
                return text.strip()
            except Exception:
                return ""
    except Exception as e:
        print(f"Error parsing resume {file_path}: {str(e)}")
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
        # Use regex to match whole words/phrases to avoid partial matches (e.g., 'go' in 'government')
        # We handle skills that start or end with non-word characters (like C++, C#, .NET)
        pattern = re.escape(skill.lower())
        
        # If it starts with a word char, require word boundary at start
        if re.match(r'^\w', pattern):
            pattern = r'\b' + pattern
        else: # Starts with non-word char like .NET
            pattern = r'(?<!\w)' + pattern
            
        # If it ends with a word char, require word boundary at end
        if re.search(r'\w$', pattern):
            pattern = pattern + r'\b'
        else: # Ends with non-word char like C++ or C#
            pattern = pattern + r'(?!\w)'
            
        if re.search(pattern, text_lower):
            found_skills.append(skill.title() if len(skill) > 3 else skill.upper())
            
    return list(set(found_skills))


def extract_education_from_text(text: str) -> List[dict]:
    """Extract education details from resume text using common patterns."""
    education = []
    
    # Common degree patterns
    degree_patterns = [
        r"(Bachelor|B\.?E\.?|B\.?Tech|B\.?S\.?|B\.?A\.?|Master|M\.?S\.?|M\.?Tech|Ph\.?D|MBA)",
        r"(Degree|Diploma|School|University|College|Institute)"
    ]
    
    # Simple line-by-line check (very basic parser)
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if not line: continue
        
        is_edu_line = False
        degree = "Degree"
        for pattern in degree_patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                is_edu_line = True
                if "bachelor" in line.lower() or "b.e" in line.lower() or "b.tech" in line.lower():
                    degree = "Bachelor's Degree"
                elif "master" in line.lower() or "m.tech" in line.lower() or "m.s" in line.lower():
                    degree = "Master's Degree"
                break
        
        if is_edu_line:
            # Try to find year
            year_match = re.search(r"(20\d{2})", line)
            year = year_match.group(1) if year_match else "2024"
            
            institution = line[:100] # Safe limit
            if " at " in line.lower():
                institution = line.lower().split(" at ")[-1].title()
            elif " from " in line.lower():
                institution = line.lower().split(" from ")[-1].title()
            
            education.append({
                "degree": degree,
                "institution": institution,
                "year": year
            })
            
    # De-duplicate and return top 2
    unique_edu = []
    seen = set()
    for e in education:
        if e["institution"] not in seen:
            unique_edu.append(e)
            seen.add(e["institution"])
            
    return unique_edu[:2] if unique_edu else []


def extract_experience_from_text(text: str) -> List[dict]:
    """Extract experience details from resume text."""
    experience = []
    
    # Common job titles or keywords indicating experience
    job_keywords = ["Developer", "Engineer", "Intern", "Analyst", "Manager", "Lead", "Consultant", "Designer"]
    
    lines = text.split('\n')
    for line in lines:
        line = line.strip()
        if not line: continue
        
        is_exp_line = False
        title = "Professional"
        for kw in job_keywords:
            if kw.lower() in line.lower():
                is_exp_line = True
                title = kw
                break
        
        if is_exp_line and (" at " in line.lower() or " | " in line or " - " in line):
            # Try to extract company
            company = "Company"
            if " at " in line.lower():
                company = line.lower().split(" at ")[-1].split(",")[0].strip().title()
            elif " | " in line:
                company = line.split("|")[0].strip()
            
            # Try to extract duration
            duration = "2023 - Present"
            if "un" in line.lower() or "jan" in line.lower() or "feb" in line.lower() or "mar" in line.lower():
                duration = "Recent"

            experience.append({
                "title": title + " Role",
                "company": company,
                "duration": duration
            })

    unique_exp = []
    seen = set()
    for exp in experience:
        if exp["company"] not in seen:
            unique_exp.append(exp)
            seen.add(exp["company"])

    return unique_exp[:2] if unique_exp else []


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

