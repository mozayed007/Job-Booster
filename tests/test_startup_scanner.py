"""Tests for the Startup Scanner module."""

import pytest

from app.models.startup_model import JobOpening, ScannerState, Startup, UserProfile
from app.services.startup_parser import (
    filter_startups,
    get_startups_by_category,
    get_startups_by_city,
    parse_startups_file,
)


class TestStartupModels:
    """Test Pydantic models."""

    def test_startup_model(self):
        """Test Startup model creation."""
        startup = Startup(
            name="TestStartup",
            city="Berlin",
            category="Medicine",
            website="https://test.com",
        )
        assert startup.name == "TestStartup"
        assert startup.city == "Berlin"
        assert startup.category == "Medicine"

    def test_job_opening_model(self):
        """Test JobOpening model with validation."""
        job = JobOpening(
            startup_name="TestStartup",
            title="ML Engineer",
            location="Remote",
            requirements=["Python", "PyTorch"],
            link="https://careers.test.com/ml-engineer",
            relevance_score=0.85,
        )
        assert job.relevance_score == 0.85
        assert len(job.requirements) == 2

    def test_job_opening_relevance_bounds(self):
        """Test relevance_score must be 0-1."""
        # Valid
        job = JobOpening(
            startup_name="Test",
            title="Engineer",
            link="https://test.com",
            relevance_score=0.5,
        )
        assert job.relevance_score == 0.5

        # Invalid - should raise
        with pytest.raises(Exception):
            JobOpening(
                startup_name="Test",
                title="Engineer",
                link="https://test.com",
                relevance_score=1.5,  # Over 1.0
            )

    def test_scanner_state_add_processed(self):
        """Test ScannerState tracks processed startups."""
        state = ScannerState()
        assert len(state.processed_startups) == 0

        state.add_processed("Startup1")
        state.add_processed("Startup2")
        state.add_processed("Startup1")  # Duplicate

        assert len(state.processed_startups) == 2

    def test_scanner_state_add_roles(self):
        """Test ScannerState keeps top roles by score."""
        state = ScannerState()

        jobs = [
            JobOpening(startup_name="A", title="Job1", link="x", relevance_score=0.5),
            JobOpening(startup_name="B", title="Job2", link="x", relevance_score=0.9),
            JobOpening(startup_name="C", title="Job3", link="x", relevance_score=0.1),
        ]
        state.add_roles(jobs)

        assert len(state.promising_roles) == 3
        assert state.promising_roles[0].relevance_score == 0.9  # Sorted desc

    def test_user_profile_defaults(self):
        """Test UserProfile has sensible defaults."""
        profile = UserProfile()
        assert "AI/ML" in profile.skills
        assert "Remote" in profile.preferred_locations


class TestStartupParser:
    """Test startup parser functionality."""

    def test_parse_startups_file(self):
        """Test parsing the startups.md file."""
        startups = parse_startups_file()

        # Should have startups
        assert len(startups) > 0

        # Should have expected fields
        assert all(s.name for s in startups)
        assert all(s.city for s in startups)
        assert all(s.category for s in startups)

    def test_filter_by_city(self):
        """Test filtering startups by city."""
        startups = parse_startups_file()
        berlin_startups = filter_startups(startups, cities=["Berlin"])

        assert all(s.city == "Berlin" for s in berlin_startups)

    def test_filter_with_website_only(self):
        """Test filtering to startups with websites."""
        startups = parse_startups_file()
        with_website = filter_startups(startups, with_website_only=True)

        assert all(s.website for s in with_website)

    def test_group_by_city(self):
        """Test grouping startups by city."""
        startups = parse_startups_file()
        by_city = get_startups_by_city(startups)

        assert isinstance(by_city, dict)
        assert len(by_city) > 0

    def test_group_by_category(self):
        """Test grouping startups by category."""
        startups = parse_startups_file()
        by_category = get_startups_by_category(startups)

        assert isinstance(by_category, dict)
        assert "Medicine" in by_category or len(by_category) > 0


class TestLLMConfig:
    """Test LLM configuration."""

    def test_get_model_name_default(self):
        """Test default model selection."""
        from app.core.model_registry import get_model_string

        model = get_model_string()

        # Should return a valid model string with provider prefix
        assert isinstance(model, str)
        assert ":" in model or "/" in model

    def test_get_model_registry_status(self):
        """Test registry status returns expected structure."""
        from app.core.model_registry import get_status

        status = get_status()

        assert "primary" in status
        assert "fallbacks" in status
        assert "providers" in status
        assert isinstance(status["providers"], dict)
