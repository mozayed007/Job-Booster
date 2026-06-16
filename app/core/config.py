"""Configuration settings for Job_Booster application."""

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

    GOOGLE_GEMINI_API_KEY: str | None = None
    GEMINI_MODEL: str = "google:gemini-3.1-flash-lite"

    API_URL: str = "http://localhost:8000"

    TINYFISH_API_KEY: str | None = None
    USE_CRAWL4AI: bool = False

    CORS_ORIGINS: str = "*"

    # Auth — a fixed JWT signing secret must be supplied in production.
    # When unset and DEBUG=False the app refuses to start (see
    # ``app.services.auth_service``). A random per-process secret is only
    # permitted for local development.
    JWT_SECRET_KEY: str | None = None
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_HOURS: int = 24

    # Paths
    RESUME_SOURCES_DIR: str = "data/resumes/sources"
    RESUME_OUTPUT_DIR: str = "data/resumes/output"
    RESUME_TEMPLATE_PATH: str = "data/templates/resume_template.tex"
    STARTUPS_FILE_PATH: str = "data/startups/startups.md"
    JOBS_DIR: str = "data/jobs"

    USER_PROFILE_PATH: str = "data/user_profile.yaml"

    BIGSET_IMPORT_DIR: str = "data/bigset_imports"
    BIGSET_DEFAULT_MAPPING: str = "generic_job_listing"
    BIGSET_SKIP_SCRAPE_HOURS: int = 0
    BIGSET_FOLDER_WATCH_CRON: str = "0 */6 * * *"
    BIGSET_FOLDER_WATCH_ENABLED: bool = True
    BIGSET_MAX_UPLOAD_BYTES: int = 52_428_800
    BIGSET_REMOTE_ENABLED: bool = False
    BIGSET_APP_URL: str = "http://localhost:3500"
    BIGSET_AUTO_SYNC_ON_PIPELINE: bool = True

    AX_MCPS_DIR: str = "mcps"
    AX_MERGE_INBOUND_MCPS: bool = True

    PIPELINE_BACKGROUND_JOB_TTL_SECONDS: int = 86_400
    PIPELINE_BACKGROUND_JOB_MAX_ENTRIES: int = 200
    PIPELINE_UI_POLL_INTERVAL_SECONDS: float = 2.0
    PIPELINE_UI_POLL_MAX_ATTEMPTS: int = 60

    model_config = {"env_file": ".env", "case_sensitive": True, "extra": "ignore"}


settings = Settings()
