"""Resume data models for Job_Booster application."""

from datetime import date
from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import Field

from .base_model import JobBoosterBase


class ContactInfo(JobBoosterBase):
    """Contact information of a person."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None


class Education(JobBoosterBase):
    """Education details."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    gpa: Optional[float] = None
    description: Optional[str] = None
    honors: Optional[List[str]] = Field(default_factory=list)


class WorkExperience(JobBoosterBase):
    """Work experience details."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    company: str
    title: str
    location: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    is_current: bool = False
    description: Optional[str] = None
    bullet_points: List[str] = Field(default_factory=list)
    technologies: List[str] = Field(default_factory=list)


class Project(JobBoosterBase):
    """Project details."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    description: Optional[str] = None
    url: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)
    bullet_points: List[str] = Field(default_factory=list)
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class Skill(JobBoosterBase):
    """Skill details."""
    name: str
    category: Optional[str] = None
    level: Optional[str] = None  # e.g. beginner, intermediate, expert


class Certification(JobBoosterBase):
    """Certification details."""
    name: str
    issuer: Optional[str] = None
    date: Optional[str] = None
    expiry_date: Optional[str] = None
    credential_id: Optional[str] = None
    url: Optional[str] = None


class Resume(JobBoosterBase):
    """Complete resume data model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    contact: Optional[ContactInfo] = None
    summary: Optional[str] = None
    objective: Optional[str] = None
    work_experience: List[WorkExperience] = Field(default_factory=list)
    education: List[Education] = Field(default_factory=list)
    skills: List[Skill] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    languages: List[str] = Field(default_factory=list)
    awards: List[str] = Field(default_factory=list)
    publications: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
