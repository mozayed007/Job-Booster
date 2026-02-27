"""Job description data models for Job_Booster application."""

from typing import Dict, List, Optional, Set
from uuid import uuid4

from pydantic import Field

from .base_model import JobBoosterBase


class Requirement(JobBoosterBase):
    """Job requirement details."""
    description: str
    is_required: bool = True  # True = required, False = preferred/nice-to-have
    category: Optional[str] = None  # e.g. education, experience, skill


class Responsibility(JobBoosterBase):
    """Job responsibility details."""
    description: str
    category: Optional[str] = None


class Benefit(JobBoosterBase):
    """Job benefit details."""
    description: str
    category: Optional[str] = None  # e.g. health, financial, lifestyle


class CompanyInfo(JobBoosterBase):
    """Company information details."""
    name: Optional[str] = None
    description: Optional[str] = None
    industry: Optional[str] = None
    size: Optional[str] = None
    website: Optional[str] = None
    location: Optional[str] = None
    culture: Optional[str] = None


class JobPosting(JobBoosterBase):
    """Complete job posting data model."""
    id: str = Field(default_factory=lambda: str(uuid4()))
    title: Optional[str] = None
    company: Optional[CompanyInfo] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None  # e.g. remote, hybrid, onsite
    employment_type: Optional[str] = None  # e.g. full-time, part-time, contract
    experience_level: Optional[str] = None  # e.g. entry, mid, senior, lead
    salary_range: Optional[str] = None
    description: Optional[str] = None
    requirements: List[Requirement] = Field(default_factory=list)
    responsibilities: List[Responsibility] = Field(default_factory=list)
    benefits: List[Benefit] = Field(default_factory=list)
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    keywords: List[str] = Field(default_factory=list)
    raw_text: Optional[str] = None
