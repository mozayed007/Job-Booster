"""Job_Booster agents — config-driven AI agents for job search automation."""

from app.agents.base_agent import BaseAgent, get_agent, load_agents, reload_agents
from app.agents.cover_letter import CoverLetterAgent, CoverLetterOutput, generate_cover_letter
from app.agents.cv_extractor import CvExtractorAgent, CVExtractorOutput, tailor_resume_from_cv
from app.agents.interview_coach import InterviewCoachAgent, InterviewCoachOutput, prep_for_interview
from app.agents.job_finder import JobFinderAgent, JobFinderOutput, find_jobs
from app.agents.outreach_agent import OutreachAgent, OutreachOutput, generate_outreach
from app.agents.resume_reviewer import ResumeReviewerAgent, ResumeReviewerOutput, review_resume
from app.agents.resume_tailor import ResumeTailorAgent, TailoredResumeOutput, tailor_resume
from app.agents.startup_scanner import StartupScannerAgent, quick_scan

__all__ = [
    # Base infrastructure
    "BaseAgent",
    "get_agent",
    "load_agents",
    "reload_agents",
    # Cover letter
    "CoverLetterAgent",
    "CoverLetterOutput",
    "generate_cover_letter",
    # CV extractor
    "CvExtractorAgent",
    "CVExtractorOutput",
    "tailor_resume_from_cv",
    # Job finder
    "JobFinderAgent",
    "JobFinderOutput",
    "find_jobs",
    # Resume reviewer
    "ResumeReviewerAgent",
    "ResumeReviewerOutput",
    "review_resume",
    # Resume tailor
    "ResumeTailorAgent",
    "TailoredResumeOutput",
    "tailor_resume",
    # Startup scanner
    "StartupScannerAgent",
    "quick_scan",
    # Outreach
    "OutreachAgent",
    "OutreachOutput",
    "generate_outreach",
    # Interview coach
    "InterviewCoachAgent",
    "InterviewCoachOutput",
    "prep_for_interview",
]
