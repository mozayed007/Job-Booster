"""SQLite table schemas for Job_Booster application."""

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """User table for storing user information."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, nullable=True)
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    profile_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ResumeDB(Base):
    """Resume table for storing parsed resume data."""

    __tablename__ = "resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    filename: Mapped[str] = mapped_column(String(255))
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    versions: Mapped[list["ResumeVersionDB"]] = relationship(
        "ResumeVersionDB", back_populates="resume"
    )


class ResumeVersionDB(Base):
    """Resume version table for tracking multiple file versions."""

    __tablename__ = "resume_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    version_name: Mapped[str] = mapped_column(String(255))
    file_path: Mapped[str] = mapped_column(String(512))
    file_format: Mapped[str] = mapped_column(String(10))
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    resume: Mapped["ResumeDB"] = relationship("ResumeDB", back_populates="versions")


class JobPostingDB(Base):
    """Job Posting table for storing parsed job description data."""

    __tablename__ = "job_postings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    content_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class TailoredResumeDB(Base):
    """Tailored Resume table for storing generated tailored resumes."""

    __tablename__ = "tailored_resumes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_postings.id"))
    tailored_content: Mapped[str] = mapped_column(Text)
    match_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class AnalysisResultDB(Base):
    """Analysis Result table for storing resume-job analysis results."""

    __tablename__ = "analysis_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int] = mapped_column(Integer, ForeignKey("resumes.id"))
    job_id: Mapped[int] = mapped_column(Integer, ForeignKey("job_postings.id"))
    analysis_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class StartupDB(Base):
    """Startup table for storing parsed startup data from startups.md"""

    __tablename__ = "startups"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), unique=True)
    city: Mapped[str] = mapped_column(String(100))
    category: Mapped[str] = mapped_column(String(100))
    website: Mapped[str | None] = mapped_column(String(512), nullable=True)
    linkedin: Mapped[str | None] = mapped_column(String(512), nullable=True)
    founded: Mapped[str | None] = mapped_column(String(20), nullable=True)
    employees: Mapped[str | None] = mapped_column(String(50), nullable=True)
    followers: Mapped[str | None] = mapped_column(String(50), nullable=True)
    funding_round: Mapped[str | None] = mapped_column(String(100), nullable=True)
    last_scanned: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    job_openings: Mapped[list["ScannedJobDB"]] = relationship(
        "ScannedJobDB", back_populates="startup"
    )


class ScannedJobDB(Base):
    """Scanned job openings found by the startup scanner agent"""

    __tablename__ = "scanned_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    startup_id: Mapped[int] = mapped_column(Integer, ForeignKey("startups.id"))
    title: Mapped[str] = mapped_column(String(255))
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    requirements_json: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    link: Mapped[str] = mapped_column(String(512))
    relevance_score: Mapped[float] = mapped_column(Float, default=0.0)
    is_applied: Mapped[bool] = mapped_column(Boolean, default=False)
    discovered_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    startup: Mapped["StartupDB"] = relationship("StartupDB", back_populates="job_openings")


class ScannerStateDB(Base):
    """Persistent scanner state for batch processing across sessions"""

    __tablename__ = "scanner_state"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    state_json: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    batch_number: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), default="in_progress")
    last_updated: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class CoverLetterDB(Base):
    """Cover Letter table for storing generated cover letters."""

    __tablename__ = "cover_letters"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    resume_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("job_postings.id"), nullable=True
    )
    cover_letter_text: Mapped[str] = mapped_column(Text)
    key_highlights_json: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class ApplicationDB(Base):
    """Application tracking table for managing job applications."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    job_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("job_postings.id"), nullable=True
    )
    resume_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("resumes.id"), nullable=True)
    company_name: Mapped[str] = mapped_column(String(255))
    position_title: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="applied")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    applied_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class PipelineRun(Base):
    """Pipeline execution history."""

    __tablename__ = "pipeline_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("users.id"), nullable=True)
    pipeline_key: Mapped[str] = mapped_column(String(100), nullable=False)
    pipeline_name: Mapped[str] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(50), default="pending")
    steps_completed: Mapped[int] = mapped_column(Integer, default=0)
    total_steps: Mapped[int] = mapped_column(Integer, default=0)
    artifacts_json: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    errors_json: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True)
    resume_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


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
