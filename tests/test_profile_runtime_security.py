"""Tests for profile runtime security helpers."""

import pytest

from profiles.runtimes.security import ProfileNotAllowedError, validate_profile_name


def test_validate_known_profile():
    """A profile declared in profiles/agents/*.yaml is accepted."""
    name = validate_profile_name("job-finder")
    assert name == "job-finder"


def test_validate_unknown_profile():
    """An undeclared profile name is rejected."""
    with pytest.raises(ProfileNotAllowedError):
        validate_profile_name("not-a-real-profile")


def test_validate_empty_name():
    """Empty names are rejected."""
    with pytest.raises(ProfileNotAllowedError):
        validate_profile_name("")
    with pytest.raises(ProfileNotAllowedError):
        validate_profile_name(None)  # type: ignore[arg-type]


def test_validate_path_traversal():
    """Names containing path separators or parent references are rejected."""
    for bad in ["../config", "..\\config", "a/b", "a\\b", "..", "."]:
        with pytest.raises(ProfileNotAllowedError):
            validate_profile_name(bad)


@pytest.mark.asyncio
async def test_run_agent_rejects_disallowed_profile():
    """generic_runner.run_agent raises for a disallowed profile name."""
    pytest.importorskip("httpx")
    from profiles.runtimes.generic_runner import run_agent

    with pytest.raises(ValueError, match="Profile not allowed"):
        await run_agent("not-a-real-profile", {})


def test_pydantic_bridge_rejects_disallowed_profile():
    """pydantic_bridge.create_agent_from_profile raises for a disallowed name."""
    from profiles.runtimes.pydantic_bridge import create_agent_from_profile

    with pytest.raises(ValueError, match="Profile not allowed"):
        create_agent_from_profile("not-a-real-profile")
