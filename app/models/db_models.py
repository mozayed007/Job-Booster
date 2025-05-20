"""SQLite table schemas for Job_Booster application."""

from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey, Integer, JSON, String, Table, Text, create_engine
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class User(Base):
    """User table for storing user information."""
    __tablename__ = "users"

    # To-Do: Define table columns and relationships
    pass


class ResumeDB(Base):
    """Resume table for storing parsed resume data."""
    __tablename__ = "resumes"

    # To-Do: Define table columns and relationships
    pass


class JobPostingDB(Base):
    """Job Posting table for storing parsed job description data."""
    __tablename__ = "job_postings"

    # To-Do: Define table columns and relationships
    pass


class TailoredResumeDB(Base):
    """Tailored Resume table for storing generated tailored resumes."""
    __tablename__ = "tailored_resumes"

    # To-Do: Define table columns and relationships
    pass


class AnalysisResultDB(Base):
    """Analysis Result table for storing resume-job analysis results."""
    __tablename__ = "analysis_results"

    # To-Do: Define table columns and relationships
    pass


def create_tables(db_url: str = "sqlite:///./job_booster.db"):
    """Creates all tables in the database."""
    engine = create_engine(db_url)
    Base.metadata.create_all(engine)