"""API models for Job_Booster application."""

from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

from .base_model import BaseResponse
from .job_model import JobPosting
from .resume_model import Resume


class ResumeParseResponse(BaseResponse):
    """Response model for resume parsing."""

    data: Optional[Resume] = None
    resume_version_id: Optional[int] = None


class JobParseResponse(BaseResponse):
    """Response model for job posting parsing."""

    data: Optional[JobPosting] = None


class JobTextRequest(BaseModel):
    """Request model for job text parsing."""

    text: str


class AnalysisRequest(BaseModel):
    """Request model for resume-job analysis."""

    resume_text: Optional[str] = None
    resume_id: Optional[UUID] = None
    job_text: Optional[str] = None
    job_id: Optional[UUID] = None


class SkillMatch(BaseModel):
    """Skill match details."""

    skill: str
    matched: bool
    confidence: float
    source: str


class ExperienceMatch(BaseModel):
    """Experience match details."""

    requirement: str
    met: bool
    evidence: Optional[str] = None


class AnalysisData(BaseModel):
    """Analysis data model."""

    overall_score: float
    skill_matches: list[SkillMatch] = Field(default_factory=list)
    experience_matches: list[ExperienceMatch] = Field(default_factory=list)
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)


class AnalysisResponse(BaseResponse):
    """Response model for resume-job analysis."""

    data: Optional[AnalysisData] = None


class TailoredResumeRequest(BaseModel):
    """Request model for tailored resume generation."""

    resume_text: str
    job_text: str
    format_type: str = "text"


class TailoredResumeData(BaseModel):
    """Tailored resume data model."""

    tailored_content: str
    improvements: list[str] = Field(default_factory=list)
    format_type: str = "text"


class TailoredResumeResponse(BaseResponse):
    """Response model for tailored resume generation."""

    data: Optional[TailoredResumeData] = None


class CoverLetterRequest(BaseModel):
    """Request model for cover letter generation."""

    resume_text: str
    job_text: str
    company_name: Optional[str] = None
    hiring_manager: Optional[str] = None


class CoverLetterData(BaseModel):
    """Cover letter data model."""

    cover_letter: str
    key_highlights: list[str] = Field(default_factory=list)
    tone: str = "professional"


class CoverLetterResponse(BaseResponse):
    """Response model for cover letter generation."""

    data: Optional[CoverLetterData] = None


class RegisterRequest(BaseModel):
    email: str
    password: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    success: bool = True
    message: str = ""
    token: Optional[str] = None
    user: Optional[dict] = None


class UserProfileResponse(BaseModel):
    success: bool = True
    user: Optional[dict] = None
