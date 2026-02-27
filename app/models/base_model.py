"""Base models for Job_Booster application."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobBoosterBase(BaseModel):
    """Base model with common fields for Job_Booster models."""

    class Config:
        """Pydantic configuration."""
        populate_by_name = True
        from_attributes = True
        json_encoders = {datetime: lambda v: v.isoformat()}


class BaseResponse(BaseModel):
    """Base response model for API endpoints."""
    success: bool = True
    message: str = "OK"
    timestamp: datetime = Field(default_factory=datetime.utcnow)
