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
    
    # Common degree patterns including secondary and higher secondary (Indian context)
    degree_patterns = [
        r"\b(Bachelor|B\.?E\.?|B\.?Tech|B\.?S\.?|B\.?A\.?|Master|M\.?Tech|M\.?S\.?|M\.?E\.?|Ph\.?D|Doctoral|Post[\s-]Graduate|Graduate|Under[\s-]Graduate|MBA|Diploma|PUC|SSLC|10th|12th)\b",
        r"\b(Secondary|Matriculation|Schooling)\b"
    ]
    
    # Common institution keywords
    inst_keywords = [
        "University", "College", "Institute", "School", "Academy", "Vidhyalaya", 
        "Polytechnic", "Foundation", "High School", "Centre", "Vidya"
    ]

    # Patterns that indicate this is NOT an education line
    blacklist_patterns = [
        r"utm_", r"objective", r"summary", r"profile", r"http", r"www\.", r"career",
        r"seek", r"opportunity", r"challenging", r"contribute", r"utilize", r"environment"
    ]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) < 3 or len(line) > 120: continue
        if any(re.search(p, line, re.IGNORECASE) for p in blacklist_patterns): continue
        
        is_edu_line = False
        degree = None
        
        # Check for degree in current, previous or next line to associate with institution
        for pattern in degree_patterns:
            # Check current line
            match = re.search(pattern, line, re.IGNORECASE)
            if not match and i > 0: # Check line above
                match = re.search(pattern, lines[i-1], re.IGNORECASE)
            if not match and i < len(lines)-1: # Check line below
                match = re.search(pattern, lines[i+1], re.IGNORECASE)
                
            if match:
                deg_text = match.group(0).lower()
                is_edu_line = True
                if "bachelor" in deg_text or "b.e" in deg_text or "b.tech" in deg_text:
                    degree = "Bachelor's Degree"
                elif "master" in deg_text or "m.tech" in deg_text or "mba" in deg_text:
                    degree = "Master's Degree"
                elif "puc" in deg_text or "12th" in deg_text:
                    degree = "PUC / 12th Standard"
                elif "sslc" in deg_text or "10th" in deg_text:
                    degree = "SSLC / 10th Standard"
                elif "diploma" in deg_text:
                    degree = "Diploma"
                else:
                    degree = deg_text.title()
                break
        
        # Check for institution keywords
        has_inst = any(re.search(r"\b" + re.escape(kw) + r"\b", line, re.IGNORECASE) for kw in inst_keywords)
        
        if has_inst:
            is_edu_line = True
            if not degree: degree = "Degree"
            
            # Try to find year/duration (Search current and 2 lines above/below)
            # Support ranges like 2020-2024 or 2023 - Present
            year_pattern = r"\b((?:19[9]\d|20[0-2]\d)(?:\s*[-–]\s*(?:20[0-2]\d|Present|Current))?)\b"
            year_match = None
            for offset in [0, 1, -1, 2, -2]:
                idx = i + offset
                if 0 <= idx < len(lines):
                    m = re.search(year_pattern, lines[idx], re.IGNORECASE)
                    if m:
                        year_match = m
                        break
            
            year = year_match.group(1).strip() if year_match else ""
            
            # Extract institution
            institution = line[:100]
            if " - " in line:
                parts = line.split(" - ")
                institution = parts[1].strip() if any(re.search(p, parts[0], re.IGNORECASE) for p in degree_patterns) else parts[0].strip()
            
            institution = re.sub(r'^[•\d\.\-\s]+', '', institution).strip()
            if institution.isupper(): institution = institution.title()

            if institution and len(institution) > 5 and not any(re.search(p, institution, re.IGNORECASE) for p in blacklist_patterns):
                education.append({
                    "degree": degree,
                    "institution": institution[:80].strip(),
                    "year": year
                })
            
    # De-duplicate and return top 3
    unique_edu = []
    seen_inst = set()
    for e in education:
        inst_lower = e["institution"].lower()
        if inst_lower not in seen_inst:
            unique_edu.append(e)
            seen_inst.add(inst_lower)
            
    return unique_edu[:3]


def extract_experience_from_text(text: str) -> List[dict]:
    """Extract experience details from resume text."""
    experience = []
    
    # Common job titles indicating experience (using word boundaries)
    job_keywords = ["Developer", "Engineer", "Intern", "Analyst", "Manager", "Lead", "Consultant", "Designer", "Specialist"]
    
    # Strictly exclude education terms from experience
    edu_indicators = ["Bachelor", "Master", "Degree", "University", "College", "Diploma", "Puc", "Sslc", "10Th", "12Th", "Institute", "School"]
    
    lines = text.split('\n')
    for i, line in enumerate(lines):
        line = line.strip()
        if len(line) < 5 or len(line) > 100: continue
        
        # Skip lines that look like education
        if any(re.search(r"\b" + e + r"\b", line, re.IGNORECASE) for e in edu_indicators):
            continue

        is_exp_line = False
        title_keyword = None
        for kw in job_keywords:
            if re.search(r"\b" + kw + r"\b", line, re.IGNORECASE):
                is_exp_line = True
                title_keyword = kw
                break
        
        if is_exp_line:
            # Try to extract company
            company = "Company"
            if " at " in line.lower():
                company = line.split(" at ")[-1].split(",")[0].strip()
            elif " | " in line:
                parts = line.split("|")
                company = parts[0].strip() if title_keyword.lower() in parts[1].lower() else parts[1].strip()
            
            if company == "Company" or len(company) < 3:
                if i > 0 and len(lines[i-1].strip()) > 3:
                     company = lines[i-1].strip()
            
            # Additional check: if company looks like a school, skip it
            if any(re.search(r"\b" + e + r"\b", company, re.IGNORECASE) for e in edu_indicators):
                continue

            # Clean company
            company = re.sub(r'^[•\d\.\-\s]+', '', company).strip()

            duration = ""
            date_pattern = r"\b((?:19[9]\d|20[0-2]\d)(?:\s*[-–]\s*(?:20[0-2]\d|Present|Current))?)\b"
            date_match = re.search(date_pattern, line, re.IGNORECASE)
            if not date_match and i < len(lines) - 1:
                date_match = re.search(date_pattern, lines[i+1], re.IGNORECASE)
            if not date_match and i > 0:
                date_match = re.search(date_pattern, lines[i-1], re.IGNORECASE)
            
            if date_match:
                duration = date_match.group(1).strip()

            experience.append({
                "title": (line.split(",")[0][:40] if len(line.split(",")[0]) < 40 else title_keyword + " Role").title(),
                "company": company[:60].title(),
                "duration": duration if duration else "Recently active"
            })

    unique_exp = []
    seen_comp = set()
    for exp in experience:
        comp_lower = exp["company"].lower()
        if comp_lower not in seen_comp and len(comp_lower) > 3:
            unique_exp.append(exp)
            seen_comp.add(comp_lower)

    return unique_exp[:3]





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

