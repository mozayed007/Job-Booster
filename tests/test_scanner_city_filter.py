"""Unit tests for scanner city filtering."""

from app.agents.startup_scanner import StartupScannerAgent
from app.models.startup_model import JobOpening, Startup


def test_get_top_roles_filters_by_city(monkeypatch):
    from app.models.startup_model import ScannerState

    agent = StartupScannerAgent.__new__(StartupScannerAgent)
    agent.state = ScannerState()
    agent.state.promising_roles = [
        JobOpening(
            startup_name="Alpha",
            title="Engineer",
            location="SF",
            link="https://a.com",
            relevance_score=0.9,
        ),
        JobOpening(
            startup_name="Beta",
            title="Designer",
            location="Remote",
            link="https://b.com",
            relevance_score=0.8,
        ),
    ]

    startups = [
        Startup(name="Alpha", city="San Francisco", category="AI", website="https://a.com"),
        Startup(name="Beta", city="Cairo", category="Fin", website="https://b.com"),
    ]
    monkeypatch.setattr(agent, "_merged_startups_with_website", lambda: startups)

    sf_jobs = agent.get_top_roles(limit=10, city="San Francisco")
    assert len(sf_jobs) == 1
    assert sf_jobs[0].startup_name == "Alpha"

    all_jobs = agent.get_top_roles(limit=10, city="All")
    assert len(all_jobs) == 2
