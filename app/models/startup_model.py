"""Startup Scanner Models - Pydantic models for type-safe job extraction."""

from datetime import datetime

from pydantic import BaseModel, Field


class Startup(BaseModel):
    """Startup entity parsed from startups.md"""

    name: str
    city: str
    category: str = Field(description="e.g., Medicine, NLP, Robotics")
    website: str | None = None
    linkedin: str | None = None
    founded: str | None = None
    employees: str | None = None
    followers: str | None = None
    funding_round: str | None = None

    model_config = {"extra": "ignore"}


class JobOpening(BaseModel):
    """Type-safe job opening - Pydantic AI guarantees valid output"""

    startup_name: str
    title: str
    location: str = Field(default="Remote")
    requirements: list[str] = Field(default_factory=list)
    link: str
    relevance_score: float = Field(
        ge=0.0, le=1.0, description="0-1 score based on match to AI/ML/GPU/distributed systems"
    )

    model_config = {"extra": "ignore"}


class ScannerState(BaseModel):
    """Persistent state for batch processing across sessions"""

    processed_startups: list[str] = Field(default_factory=list)
    last_city_processed: str = ""
    batch_number: int = 0
    total_estimated_batches: int = 0
    promising_roles: list[JobOpening] = Field(default_factory=list)
    status: str = Field(default="in_progress", pattern="^(in_progress|paused|complete)$")
    last_updated: datetime = Field(default_factory=datetime.now)

    def add_processed(self, startup_name: str) -> None:
        """Mark startup as processed"""
        if startup_name not in self.processed_startups:
            self.processed_startups.append(startup_name)
        self.last_updated = datetime.now()

    def add_roles(self, roles: list[JobOpening]) -> None:
        """Add promising roles, keeping top by relevance"""
        self.promising_roles.extend(roles)
        self.promising_roles.sort(key=lambda x: x.relevance_score, reverse=True)
        self.promising_roles = self.promising_roles[:100]  # Keep top 100
        self.last_updated = datetime.now()


class UserProfile(BaseModel):
    """User's background for relevance scoring"""

    skills: list[str] = Field(
        default_factory=lambda: [
            "AI/ML",
            "Deep Learning",
            "GPU/CUDA",
            "Distributed Systems",
            "MoE",
            "Multimodal",
            "EEG",
            "Scaling",
            "Research",
            "Python",
        ]
    )
    preferred_locations: list[str] = Field(default_factory=lambda: ["Remote", "EU", "Cairo"])
    preferred_categories: list[str] = Field(
        default_factory=lambda: [
            "Medicine",
            "NLP",
            "Robotics",
            "Science & Engineering",
            "Business",
            "Consulting",
            "Other",
        ]
    )
    visa_support_required: bool = True
