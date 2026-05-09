"""Configuration settings for Job_Booster application."""

from typing import Optional

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

load_dotenv()


class Settings(BaseSettings):
    """Application settings."""

    HOST: str = "0.0.0.0"
    PORT: int = 8000
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./job_booster.db"

    GOOGLE_GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL: str = "gemini-pro"

    API_URL: str = "http://localhost:8000"

    TINYFISH_API_KEY: Optional[str] = None
    USE_CRAWL4AI: bool = False

    # Paths
    RESUME_SOURCES_DIR: str = "data/resumes/sources"
    RESUME_OUTPUT_DIR: str = "data/resumes/output"
    RESUME_TEMPLATE_PATH: str = "data/templates/resume_template.tex"
    STARTUPS_FILE_PATH: str = "data/startups/startups.md"
    JOBS_DIR: str = "data/jobs"

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
