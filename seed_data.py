"""
seed_data.py
============
Run once to populate the database with the sample data previously held in
the frontend's mockData.js file.

Usage (from InternLink_team-5 directory):
    python seed_data.py
"""

import sys
import os
from datetime import datetime, timedelta

# Make sure we can import project modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal, create_tables
from models.user import User, UserProfile
from models.recruiter import RecruiterProfile
from models.job import Job
from models.social import Post, Comment
from services.auth_service import hash_password

# ---------------------------------------------------------------------------
# Seed configuration
# ---------------------------------------------------------------------------

RECRUITER_PASSWORD = "Password123!"

RECRUITERS = [
    {
        "email": "hr@technova.com",
        "company_name": "TechNova Solutions",
        "industry": "Technology",
        "headquarters": "Bengaluru, India",
    },
    {
        "email": "recruit@cloudsync.com",
        "company_name": "CloudSync Labs",
        "industry": "Cloud Computing",
        "headquarters": "Hyderabad, India",
    },
    {
        "email": "hr@analytiq.com",
        "company_name": "AnalytiQ Corp",
        "industry": "Data & Analytics",
        "headquarters": "Mumbai, India",
    },
    {
        "email": "jobs@pixelcraft.com",
        "company_name": "PixelCraft Studio",
        "industry": "Design",
        "headquarters": "Remote",
    },
    {
        "email": "careers@infraedge.com",
        "company_name": "InfraEdge Technologies",
        "industry": "Infrastructure",
        "headquarters": "Pune, India",
    },
    {
        "email": "hire@appverse.com",
        "company_name": "AppVerse Inc",
        "industry": "Mobile",
        "headquarters": "Chennai, India",
    },
]

# Each entry maps to a recruiter company_name
JOBS = [
    {
        "company": "TechNova Solutions",
        "title": "Frontend Developer Intern",
        "description": "Join our dynamic team to build responsive web applications using React. You will work on real projects, collaborate with senior developers, and gain hands-on experience in modern web development.",
        "requirements": ["Currently pursuing B.Tech/MCA", "Knowledge of React & JavaScript", "Good communication skills"],
        "skills_required": ["React", "JavaScript", "CSS", "Git"],
        "location": "Bengaluru, India",
        "is_remote": False,
        "stipend_min": 15000,
        "stipend_max": 15000,
        "job_type": "internship",
        "deadline_days": 24,
        "openings": 3,
    },
    {
        "company": "CloudSync Labs",
        "title": "Backend Developer",
        "description": "Design and develop scalable RESTful APIs. Work with microservices architecture and cloud-native technologies.",
        "requirements": ["2+ years experience", "Strong Python skills", "Database design knowledge"],
        "skills_required": ["Python", "FastAPI", "PostgreSQL", "Docker"],
        "location": "Hyderabad, India",
        "is_remote": False,
        "stipend_min": 66666,
        "stipend_max": 80000,
        "job_type": "full-time",
        "deadline_days": 39,
        "openings": 1,
    },
    {
        "company": "AnalytiQ Corp",
        "title": "Data Science Intern",
        "description": "Analyze large datasets, build ML models, and create insightful dashboards. Perfect for aspiring data scientists.",
        "requirements": ["Knowledge of Python & ML", "Statistics fundamentals", "Currently pursuing a degree"],
        "skills_required": ["Python", "Pandas", "Machine Learning", "SQL"],
        "location": "Mumbai, India",
        "is_remote": False,
        "stipend_min": 20000,
        "stipend_max": 20000,
        "job_type": "internship",
        "deadline_days": 41,
        "openings": 2,
    },
    {
        "company": "PixelCraft Studio",
        "title": "UI/UX Design Intern",
        "description": "Create stunning user interfaces and conduct user research. Transform complex requirements into elegant designs.",
        "requirements": ["Portfolio of design work", "Figma proficiency", "UX research experience"],
        "skills_required": ["Figma", "Adobe XD", "Prototyping", "User Research"],
        "location": "Remote",
        "is_remote": True,
        "stipend_min": 12000,
        "stipend_max": 12000,
        "job_type": "internship",
        "deadline_days": 29,
        "openings": 2,
    },
    {
        "company": "InfraEdge Technologies",
        "title": "DevOps Engineer",
        "description": "Build and maintain cloud infrastructure. Implement CI/CD pipelines and ensure 99.9% uptime.",
        "requirements": ["3+ years DevOps experience", "AWS certified preferred", "Strong Linux skills"],
        "skills_required": ["AWS", "Kubernetes", "Terraform", "CI/CD"],
        "location": "Pune, India",
        "is_remote": False,
        "stipend_min": 100000,
        "stipend_max": 120000,
        "job_type": "full-time",
        "deadline_days": 55,
        "openings": 1,
    },
    {
        "company": "AppVerse Inc",
        "title": "Mobile App Developer Intern",
        "description": "Develop cross-platform mobile applications using React Native. Deploy apps on both iOS and Android.",
        "requirements": ["React Native knowledge", "Published app is a plus", "API integration experience"],
        "skills_required": ["React Native", "JavaScript", "Firebase", "REST APIs"],
        "location": "Chennai, India",
        "is_remote": False,
        "stipend_min": 18000,
        "stipend_max": 18000,
        "job_type": "internship",
        "deadline_days": 34,
        "openings": 3,
    },
]

DEMO_USER = {
    "email": "demo@internlink.com",
    "password": "Demo1234!",
    "full_name": "InternLink Demo",
}

POSTS = [
    {
        "content": "Just completed my 6-month internship at TechNova and got a full-time offer! 🎉 The journey from an intern to a full-time Software Engineer has been amazing. Key takeaway: Never stop learning and always ask questions!",
        "author": "Priya Sharma",
        "role_label": "Software Engineer at Google",
    },
    {
        "content": "📢 Hiring Alert! We're looking for Data Science interns at Microsoft Hyderabad. If you're passionate about ML and AI, drop me a DM. Stipend: ₹50,000/month + mentorship from senior data scientists. #Hiring #DataScience #Internship",
        "author": "Aditya Patel",
        "role_label": "Data Scientist at Microsoft",
    },
    {
        "content": "5 tips for acing your design internship interview:\n1. Show your process, not just final designs\n2. Practice whiteboard challenges\n3. Research the company's design system\n4. Prepare a case study presentation\n5. Ask thoughtful questions about the team culture\n\n#DesignTips #CareerAdvice",
        "author": "Neha Gupta",
        "role_label": "Product Designer at Figma",
    },
]


def seed():
    create_tables()
    db = SessionLocal()
    try:
        # ---- Recruiter accounts + RecruiterProfiles ---- #
        recruiter_map = {}  # company_name -> RecruiterProfile
        for rec_data in RECRUITERS:
            existing = db.query(User).filter(User.email == rec_data["email"]).first()
            if existing:
                profile = db.query(RecruiterProfile).filter(
                    RecruiterProfile.user_id == existing.id
                ).first()
                recruiter_map[rec_data["company_name"]] = profile
                print(f"  [skip] Recruiter already exists: {rec_data['email']}")
                continue

            user = User(
                email=rec_data["email"],
                password_hash=hash_password(RECRUITER_PASSWORD),
                role="recruiter",
            )
            db.add(user)
            db.flush()  # get user.id

            # Empty user profile
            user_profile = UserProfile(user_id=user.id)
            db.add(user_profile)

            # Recruiter profile
            r_profile = RecruiterProfile(
                user_id=user.id,
                company_name=rec_data["company_name"],
                industry=rec_data.get("industry"),
                headquarters=rec_data.get("headquarters"),
            )
            db.add(r_profile)
            db.flush()
            recruiter_map[rec_data["company_name"]] = r_profile
            print(f"  [created] Recruiter: {rec_data['email']} ({rec_data['company_name']})")

        db.commit()

        # ---- Jobs ---- #
        for job_data in JOBS:
            company = job_data["company"]
            recruiter_profile = recruiter_map.get(company)
            if not recruiter_profile:
                print(f"  [warn] No recruiter found for company: {company}, skipping job.")
                continue

            # Check if this job title already exists for this recruiter
            existing_job = db.query(Job).filter(
                Job.recruiter_id == recruiter_profile.id,
                Job.title == job_data["title"],
            ).first()
            if existing_job:
                print(f"  [skip] Job already exists: {job_data['title']} @ {company}")
                continue

            deadline = datetime.utcnow() + timedelta(days=job_data["deadline_days"])
            job = Job(
                recruiter_id=recruiter_profile.id,
                title=job_data["title"],
                description=job_data["description"],
                requirements=job_data["requirements"],
                skills_required=job_data["skills_required"],
                location=job_data["location"],
                is_remote=job_data["is_remote"],
                stipend_min=job_data["stipend_min"],
                stipend_max=job_data["stipend_max"],
                job_type=job_data["job_type"],
                openings=job_data["openings"],
                deadline=deadline,
                is_approved=True,  # pre-approved seed data
                is_active=True,
            )
            db.add(job)
            print(f"  [created] Job: {job_data['title']} @ {company}")

        db.commit()

        # ---- Demo user for social posts ---- #
        demo_user = db.query(User).filter(User.email == DEMO_USER["email"]).first()
        if not demo_user:
            demo_user = User(
                email=DEMO_USER["email"],
                password_hash=hash_password(DEMO_USER["password"]),
                role="user",
            )
            db.add(demo_user)
            db.flush()

            demo_profile = UserProfile(
                user_id=demo_user.id,
                full_name=DEMO_USER["full_name"],
            )
            db.add(demo_profile)
            db.flush()
            db.commit()
            print(f"  [created] Demo user: {DEMO_USER['email']}")
        else:
            print(f"  [skip] Demo user already exists: {DEMO_USER['email']}")

        # ---- Social Posts ---- #
        existing_posts_count = db.query(Post).filter(Post.user_id == demo_user.id).count()
        if existing_posts_count == 0:
            for post_data in POSTS:
                post = Post(
                    user_id=demo_user.id,
                    content=post_data["content"],
                )
                db.add(post)
                print(f"  [created] Post by {post_data['author']}")
            db.commit()
        else:
            print(f"  [skip] Posts already exist for demo user ({existing_posts_count} posts)")

        print("\n✅ Seed complete!")
        print("\nRecruiter login credentials (for testing):")
        for rec_data in RECRUITERS:
            print(f"  {rec_data['email']} / {RECRUITER_PASSWORD}")
        print(f"\nDemo user: {DEMO_USER['email']} / {DEMO_USER['password']}")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Seed failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("🌱 Seeding InternLink database...\n")
    seed()
