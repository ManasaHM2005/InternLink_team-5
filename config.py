from pydantic_settings import BaseSettings
import os


class Settings(BaseSettings):
    APP_NAME: str = "InternLink API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL")

    # JWT
    JWT_SECRET_KEY: str = "internlink-super-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # File Uploads
    UPLOAD_DIR: str = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_RESUME_SIZE_MB: int = 10
    ALLOWED_RESUME_EXTENSIONS: list = [".pdf", ".doc", ".docx", ".txt"]

    class Config:
        env_file = ".env"


settings = Settings()

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "resumes"), exist_ok=True)
os.makedirs(os.path.join(settings.UPLOAD_DIR, "media"), exist_ok=True)
