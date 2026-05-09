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
    raw_text: Optional[str] = None
    parsed_data: Optional["Resume"] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True


class ContactInfo(JobBoosterBase):
    """Contact information of a person."""

    name: str = ""
    email: Optional[str] = None
    phone: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None


class Education(JobBoosterBase):
    """Education details."""

    institution: str
    degree: str
    field_of_study: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    gpa: Optional[float] = None


class WorkExperience(JobBoosterBase):
    """Work experience details."""

    company: str
    position: str
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    location: Optional[str] = None
    description: str = ""
    achievements: list[str] = Field(default_factory=list)
    skills_used: list[str] = Field(default_factory=list)


class Project(JobBoosterBase):
    """Project details."""

    name: str
    description: str = ""
    technologies: list[str] = Field(default_factory=list)
    url: Optional[str] = None


class Skill(JobBoosterBase):
    """Skill details."""

    name: str
    category: Optional[str] = None
    proficiency: Optional[str] = None
    years_of_experience: Optional[int] = None


class Certification(JobBoosterBase):
    """Certification details."""

    name: str
    issuer: Optional[str] = None
    date: Optional[date] = None
    url: Optional[str] = None


class Resume(JobBoosterBase):
    """Complete structured resume data (parsed output).
    Field names match test_resume_models.py expectations.
    """

    contact_info: ContactInfo = Field(default_factory=ContactInfo)
    summary: Optional[str] = None
    skills: list[Skill] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    work_experience: list[WorkExperience] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    raw_text: Optional[str] = None
