"""Base models for Job_Booster application."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, validator


class JobBoosterBase(BaseModel):
    """Base model with common fields for Job_Booster models."""
    # To-Do: Define model fields and Config
    pass


class BaseResponse(BaseModel):
    """Base response model for API endpoints."""
    # To-Do: Define model fields
    pass