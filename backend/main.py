from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from database import create_tables
from routes.auth_routes import router as auth_router
from routes.user_routes import router as user_router
from routes.recruiter_routes import router as recruiter_router
from routes.admin_routes import router as admin_router
from routes.social_routes import router as social_router
from routes.notification_routes import router as notification_router
from routes.interview_routes import router as interview_router
from routes.ai_routes import router as ai_router
from config import settings

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="""
    InternLink API - A comprehensive internship/job platform backend.

    ## Features
    - **User Role**: Register, profile, resume upload, job search, apply, track status, social features
    - **Recruiter**: Post jobs, view/filter applicants, download resumes, change status, analytics
    - **Admin**: Manage users/recruiters, approve jobs, analytics, handle disputes
    - **AI Upgrades**: Smart resume matching, recommendations, skill gap analysis, interview prep
    - **Real-time**: WebSocket notifications, video interview platform
    """,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth_router)
app.include_router(user_router)
app.include_router(recruiter_router)
app.include_router(admin_router)
app.include_router(social_router)
app.include_router(notification_router)
app.include_router(interview_router)
app.include_router(ai_router)


@app.on_event("startup")
def startup():
    """Create database tables on startup."""
    create_tables()
    print(f"🚀 {settings.APP_NAME} v{settings.APP_VERSION} started!")
    print(f"📄 API Docs: http://127.0.0.1:8000/docs")


@app.get("/", tags=["Root"])
def root():
    return {
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
        "status": "running",
    }


@app.get("/health", tags=["Root"])
def health_check():
    return {"status": "healthy"}
