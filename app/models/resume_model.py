"""Resume data models for Job_Booster application."""

from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import Field

from .base_model import JobBoosterBase


class ResumeFormat(str, Enum):
    """Supported resume file formats."""

    PDF = "pdf"
    DOCX = "docx"
    MARKDOWN = "md"
    TEXT = "txt"
    LATEX = "tex"


class ResumeVersion(JobBoosterBase):
    """A specific file version of a resume."""

    resume_id: UUID
    version_name: str
    file_path: str
    file_format: ResumeFormat
    raw_text: str | None = None
    parsed_data: Optional["Resume"] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class ContactInfo(JobBoosterBase):
    """Contact information of a person."""

    name: str = ""
    email: str | None = None
    phone: str | None = None
    linkedin: str | None = None
    github: str | None = None
    location: str | None = None
    website: str | None = None


class Education(JobBoosterBase):
    """Education details."""

    institution: str
    degree: str
    field_of_study: str
    start_date: date | None = None
    end_date: date | None = None
    gpa: float | None = None


class WorkExperience(JobBoosterBase):
    """Work experience details."""

    company: str
    position: str
    start_date: date | None = None
    end_date: date | None = None
    location: str | None = None
    description: str = ""
    achievements: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)


class Project(JobBoosterBase):
    """Project details."""

    name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    url: str | None = None


class Skill(JobBoosterBase):
    """Skill details."""

    name: str
    category: str | None = None
    proficiency: str | None = None
    years_of_experience: int | None = None


class Certification(JobBoosterBase):
    """Certification details."""

    name: str
    issuer: str | None = None
    cert_date: date | None = None
    url: str | None = None


class Resume(JobBoosterBase):
    """Complete structured resume data (parsed output).
    Field names match test_resume_models.py expectations.
    """

    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: str | None = None
    skills: list[Skill] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    raw_text: str | None = None
