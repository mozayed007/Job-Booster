"""SQLite table schemas for Job_Booster application."""

from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User table for storing user information."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String(255), unique=True, nullable=True)
    name = Column(String(255), nullable=True)
    profile_json = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class ResumeDB(Base):
    """Resume table for storing parsed resume data."""

    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    filename = Column(String(255))
    content_json = Column(JSON)
    raw_text = Column(Text, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    versions = relationship("ResumeVersionDB", back_populates="resume")


class ResumeVersionDB(Base):
    """Resume version table for tracking multiple file versions."""

    __tablename__ = "resume_versions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    version_name = Column(String(255))
    file_path = Column(String(512))
    file_format = Column(String(10))
    raw_text = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=_utcnow)

    resume = relationship("ResumeDB", back_populates="versions")


class JobPostingDB(Base):
    """Job Posting table for storing parsed job description data."""

    __tablename__ = "job_postings"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(255))
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    content_json = Column(JSON)
    raw_text = Column(Text, nullable=True)
    source_url = Column(String(512), nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class TailoredResumeDB(Base):
    """Tailored Resume table for storing generated tailored resumes."""

    __tablename__ = "tailored_resumes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    tailored_content = Column(Text)
    match_score = Column(Float, nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class AnalysisResultDB(Base):
    """Analysis Result table for storing resume-job analysis results."""

    __tablename__ = "analysis_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"))
    job_id = Column(Integer, ForeignKey("job_postings.id"))
    analysis_json = Column(JSON)
    created_at = Column(DateTime, default=_utcnow)


class StartupDB(Base):
    """Startup table for storing parsed startup data from startups.md"""

    __tablename__ = "startups"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), unique=True)
    city = Column(String(100))
    category = Column(String(100))
    website = Column(String(512), nullable=True)
    linkedin = Column(String(512), nullable=True)
    founded = Column(String(20), nullable=True)
    employees = Column(String(50), nullable=True)
    followers = Column(String(50), nullable=True)
    funding_round = Column(String(100), nullable=True)
    last_scanned = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=_utcnow)

    job_openings = relationship("ScannedJobDB", back_populates="startup")


class ScannedJobDB(Base):
    """Scanned job openings found by the startup scanner agent"""

    __tablename__ = "scanned_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    startup_id = Column(Integer, ForeignKey("startups.id"))
    title = Column(String(255))
    location = Column(String(255), nullable=True)
    requirements_json = Column(JSON, nullable=True)
    link = Column(String(512))
    relevance_score = Column(Float, default=0.0)
    is_applied = Column(Boolean, default=False)
    discovered_at = Column(DateTime, default=_utcnow)

    startup = relationship("StartupDB", back_populates="job_openings")


class ScannerStateDB(Base):
    """Persistent scanner state for batch processing across sessions"""

    __tablename__ = "scanner_state"

    id = Column(Integer, primary_key=True, autoincrement=True)
    state_json = Column(JSON)
    batch_number = Column(Integer, default=0)
    status = Column(String(20), default="in_progress")
    last_updated = Column(DateTime, default=_utcnow)


class CoverLetterDB(Base):
    """Cover Letter table for storing generated cover letters."""

    __tablename__ = "cover_letters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=True)
    cover_letter_text = Column(Text)
    key_highlights_json = Column(JSON, nullable=True)
    company_name = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=_utcnow)


class ApplicationDB(Base):
    """Application tracking table for managing job applications."""

    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    job_id = Column(Integer, ForeignKey("job_postings.id"), nullable=True)
    resume_id = Column(Integer, ForeignKey("resumes.id"), nullable=True)
    company_name = Column(String(255))
    position_title = Column(String(255))
    status = Column(String(50), default="applied")
    notes = Column(Text, nullable=True)
    applied_at = Column(DateTime, default=_utcnow)
    updated_at = Column(DateTime, default=_utcnow, onupdate=_utcnow)


class PipelineRun(Base):
    """Pipeline execution history."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    pipeline_key = Column(String(100), nullable=False)
    pipeline_name = Column(String(255))
    status = Column(String(50), default="pending")
    steps_completed = Column(Integer, default=0)
    total_steps = Column(Integer, default=0)
    artifacts_json = Column(JSON, nullable=True)
    errors_json = Column(JSON, nullable=True)
    resume_text = Column(Text, nullable=True)
    job_text = Column(Text, nullable=True)
    started_at = Column(DateTime, default=_utcnow)
    completed_at = Column(DateTime, nullable=True)


def create_tables(engine_or_url):
    """Creates all tables in the database.

    Args:
        engine_or_url: Either a SQLAlchemy Engine or a database URL string.
    """
    if isinstance(engine_or_url, str):
        engine = create_engine(engine_or_url)
    else:
        engine = engine_or_url
    Base.metadata.create_all(engine)
