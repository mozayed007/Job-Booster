"""Job description data models for Job_Booster application."""


from pydantic import BaseModel, Field

from .base_model import JobBoosterBase


class CompanyInfo(JobBoosterBase):
    """Company information details."""

    name: str
    industry: str | None = None
    location: str | None = None
    website: str | None = None
    description: str | None = None
    size: str | None = None


class Requirement(JobBoosterBase):
    """Job requirement details."""

    description: str
    is_required: bool = True
    category: str | None = None
    extracted_skills: list[str] = Field(default_factory=list)


class Responsibility(JobBoosterBase):
    """Job responsibility details."""

    description: str
    extracted_skills: list[str] = Field(default_factory=list)


class Benefit(JobBoosterBase):
    """Job benefit details."""

    description: str
    category: str | None = None


class JobPosting(JobBoosterBase):
    """Complete job posting data model."""

    title: str
    company_info: CompanyInfo = Field(default_factory=lambda: CompanyInfo(name=""))
    description: str = ""
    location: str | None = None
    job_type: str | None = None
    experience_level: str | None = None
    requirements: list[Requirement] = Field(default_factory=list)
    responsibilities: list[Responsibility] = Field(default_factory=list)
    benefits: list[Benefit] = Field(default_factory=list)
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    source_url: str | None = None


class ScrapedJob(BaseModel):
    """Lightweight model for jobs discovered from external sources."""

    model_config = {"extra": "ignore"}

    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    source: str = ""
