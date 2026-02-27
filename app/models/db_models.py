"""SQLite table schemas for Job_Booster application."""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


def generate_uuid() -> str:
    return str(uuid4())


class User(Base):
    """User table for storing user information."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resumes = relationship("ResumeDB", back_populates="user", cascade="all, delete-orphan")
    job_postings = relationship("JobPostingDB", back_populates="user", cascade="all, delete-orphan")
    tailored_resumes = relationship("TailoredResumeDB", back_populates="user", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResultDB", back_populates="user", cascade="all, delete-orphan")


class ResumeDB(Base):
    """Resume table for storing parsed resume data."""
    __tablename__ = "resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    file_path = Column(String(512), nullable=True)
    file_type = Column(String(50), nullable=True)  # pdf, docx, txt
    content = Column(Text, nullable=True)  # Raw text content
    parsed_data = Column(JSON, nullable=True)  # Structured JSON from parser
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="resumes")
    tailored_resumes = relationship("TailoredResumeDB", back_populates="original_resume", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResultDB", back_populates="resume", cascade="all, delete-orphan")


class JobPostingDB(Base):
    """Job Posting table for storing parsed job description data."""
    __tablename__ = "job_postings"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    title = Column(String(255), nullable=True)
    company = Column(String(255), nullable=True)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)  # Raw job description text
    parsed_data = Column(JSON, nullable=True)  # Structured JSON from parser
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="job_postings")
    tailored_resumes = relationship("TailoredResumeDB", back_populates="job_posting", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResultDB", back_populates="job_posting", cascade="all, delete-orphan")


class TailoredResumeDB(Base):
    """Tailored Resume table for storing generated tailored resumes."""
    __tablename__ = "tailored_resumes"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    original_resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=True, index=True)
    job_posting_id = Column(String(36), ForeignKey("job_postings.id"), nullable=True, index=True)
    content = Column(Text, nullable=True)  # The tailored resume content (text/html/markdown)
    format = Column(String(50), nullable=True)  # text, html, pdf, docx
    improvements = Column(JSON, nullable=True)  # JSON list/dict of improvements made
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="tailored_resumes")
    original_resume = relationship("ResumeDB", back_populates="tailored_resumes")
    job_posting = relationship("JobPostingDB", back_populates="tailored_resumes")


class AnalysisResultDB(Base):
    """Analysis Result table for storing resume-job analysis results."""
    __tablename__ = "analysis_results"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=True, index=True)
    resume_id = Column(String(36), ForeignKey("resumes.id"), nullable=True, index=True)
    job_posting_id = Column(String(36), ForeignKey("job_postings.id"), nullable=True, index=True)
    match_score = Column(Float, nullable=True)  # 0.0 to 100.0
    analysis_data = Column(JSON, nullable=True)  # Detailed analysis JSON
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="analysis_results")
    resume = relationship("ResumeDB", back_populates="analysis_results")
    job_posting = relationship("JobPostingDB", back_populates="analysis_results")


def create_tables(engine_or_url=None):
    """Creates all tables in the database.
    
    Args:
        engine_or_url: A SQLAlchemy engine instance or a database URL string.
                       Defaults to SQLite file 'job_booster.db'.
    """
    from sqlalchemy import create_engine as sa_create_engine
    from sqlalchemy.engine import Engine

    if engine_or_url is None:
        engine = sa_create_engine("sqlite:///./job_booster.db", connect_args={"check_same_thread": False})
    elif isinstance(engine_or_url, str):
        engine = sa_create_engine(engine_or_url, connect_args={"check_same_thread": False} if engine_or_url.startswith("sqlite") else {})
    else:
        # Assume it's an Engine instance
        engine = engine_or_url

    Base.metadata.create_all(bind=engine)
