"""Resume data models for Job_Booster application."""

from datetime import date
from typing import Dict, List, Optional, Set

from pydantic import Field

from .base_model import JobBoosterBase


class ContactInfo(JobBoosterBase):
    """Contact information of a person."""
    # To-Do: Define model fields
    pass


class Education(JobBoosterBase):
    """Education details."""
    # To-Do: Define model fields
    pass


class WorkExperience(JobBoosterBase):
    """Work experience details."""
    # To-Do: Define model fields
    pass


class Project(JobBoosterBase):
    """Project details."""
    # To-Do: Define model fields
    pass


class Skill(JobBoosterBase):
    """Skill details."""
    # To-Do: Define model fields
    pass


class Certification(JobBoosterBase):
    """Certification details."""
    # To-Do: Define model fields
    pass


class Resume(JobBoosterBase):
    """Complete resume data model."""
    # To-Do: Define model fields
    class Config:
        # To-Do: Define Config
        pass