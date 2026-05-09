"""Base models for Job_Booster application."""

from datetime import datetime, timezone
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class JobBoosterBase(BaseModel):
    """Base model with common fields for Job_Booster models."""

    id: UUID = Field(default_factory=uuid4)


class BaseResponse(BaseModel):
    """Base response model for API endpoints."""

    success: bool = True
    message: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
