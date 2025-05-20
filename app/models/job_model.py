"""Job description data models for Job_Booster application."""

from typing import Dict, List, Optional, Set

from pydantic import Field

from .base_model import JobBoosterBase


class Requirement(JobBoosterBase):
    """Job requirement details."""
    # To-Do: Define model fields
    pass


class Responsibility(JobBoosterBase):
    """Job responsibility details."""
    # To-Do: Define model fields
    pass


class Benefit(JobBoosterBase):
    """Job benefit details."""
    # To-Do: Define model fields
    pass


class CompanyInfo(JobBoosterBase):
    """Company information details."""
    # To-Do: Define model fields
    pass


class JobPosting(JobBoosterBase):
    """Complete job posting data model."""
    # To-Do: Define model fields
    class Config:
        # To-Do: Define schema_extra
        pass