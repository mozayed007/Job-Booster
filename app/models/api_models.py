"""API models for Job_Booster application."""

from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from .base_model import BaseResponse
from .job_model import JobPosting
from .resume_model import Resume


# ---------------------------------------------------------------------------
# Resume parsing
# ---------------------------------------------------------------------------

class ResumeParseResponse(BaseResponse):
    """Response model for resume parsing."""
    resume: Optional[Resume] = None
    raw_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Job posting parsing
# ---------------------------------------------------------------------------

class JobParseRequest(BaseModel):
    """Request model for job posting parsing."""
    job_text: str = Field(..., description="Raw job description text to parse")


class JobParseResponse(BaseResponse):
    """Response model for job posting parsing."""
    job: Optional[JobPosting] = None
    raw_text: Optional[str] = None


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class AnalysisRequest(BaseModel):
    """Request model for resume-job analysis."""
    resume_id: Optional[str] = Field(None, description="ID of a previously stored resume")
    job_id: Optional[str] = Field(None, description="ID of a previously stored job posting")
    resume_data: Optional[Dict[str, Any]] = Field(None, description="Resume data as a dict (alternative to resume_id)")
    job_data: Optional[Dict[str, Any]] = Field(None, description="Job data as a dict (alternative to job_id)")


class SkillMatch(BaseModel):
    """Skill match details."""
    skill: str
    in_resume: bool
    in_job: bool
    match_type: Optional[str] = None  # exact, partial, semantic


class ExperienceMatch(BaseModel):
    """Experience match details."""
    experience_id: str
    relevance_score: float
    matching_keywords: List[str] = Field(default_factory=list)
    notes: Optional[str] = None


class AnalysisData(BaseModel):
    """Analysis data model."""
    match_score: float = Field(0.0, ge=0.0, le=100.0)
    skill_matches: List[SkillMatch] = Field(default_factory=list)
    experience_matches: List[ExperienceMatch] = Field(default_factory=list)
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    gaps: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class AnalysisResponse(BaseResponse):
    """Response model for resume-job analysis."""
    analysis: Optional[AnalysisData] = None
    resume_id: Optional[str] = None
    job_id: Optional[str] = None


# ---------------------------------------------------------------------------
# Tailored resume generation
# ---------------------------------------------------------------------------

class TailoredResumeRequest(BaseModel):
    """Request model for tailored resume generation."""
    resume_id: Optional[str] = Field(None, description="ID of a previously stored resume")
    job_id: Optional[str] = Field(None, description="ID of a previously stored job posting")
    resume_data: Optional[Dict[str, Any]] = Field(None, description="Resume data as a dict (alternative to resume_id)")
    job_data: Optional[Dict[str, Any]] = Field(None, description="Job data as a dict (alternative to job_id)")
    format_type: str = Field("text", description="Output format: text, html, pdf, docx")


class TailoredResumeData(BaseModel):
    """Tailored resume data model."""
    content: str = Field(..., description="Tailored resume content")
    format_type: str = Field("text", description="Format of the content")
    improvements: List[str] = Field(default_factory=list, description="List of improvements made")
    match_score: Optional[float] = None


class TailoredResumeResponse(BaseResponse):
    """Response model for tailored resume generation."""
    tailored_resume: Optional[TailoredResumeData] = None
    resume_id: Optional[str] = None
    job_id: Optional[str] = None
    tailored_resume_id: Optional[str] = None
