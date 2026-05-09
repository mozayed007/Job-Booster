"""Job description data models for Job_Booster application."""

from typing import Optional

from pydantic import Field

from .base_model import JobBoosterBase


class CompanyInfo(JobBoosterBase):
    """Company information details."""

    name: str
    industry: Optional[str] = None
    location: Optional[str] = None
    website: Optional[str] = None
    description: Optional[str] = None
    size: Optional[str] = None


class Requirement(JobBoosterBase):
    """Job requirement details."""

    description: str
    is_required: bool = True
    category: Optional[str] = None
    extracted_skills: list[str] = Field(default_factory=list)


class Responsibility(JobBoosterBase):
    """Job responsibility details."""

    description: str
    extracted_skills: list[str] = Field(default_factory=list)


class Benefit(JobBoosterBase):
    """Job benefit details."""

    description: str
    category: Optional[str] = None


class JobPosting(JobBoosterBase):
    """Complete job posting data model."""

    title: str
    company_info: CompanyInfo = Field(default_factory=lambda: CompanyInfo(name=""))
    description: str = ""
    location: Optional[str] = None
    job_type: Optional[str] = None
    experience_level: Optional[str] = None
    requirements: list[Requirement] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    benefits: list[Benefit] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    source_url: Optional[str] = None
