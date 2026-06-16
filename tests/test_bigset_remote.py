"""Tests for BigSet remote dataset planning."""

from app.models.startup_model import UserProfile
from app.services.bigset_remote_service import persist_dataset_goal, profile_to_dataset_goal


class TestBigSetRemote:
    def test_profile_to_dataset_goal(self):
        profile = UserProfile(
            skills=["Python"],
            target_role_keywords=["engineer"],
            preferred_locations=["Remote"],
        )
        goal = profile_to_dataset_goal(profile)
        assert "Python" in goal
        assert "engineer" in goal
        assert "dataset" in goal.lower()

    def test_persist_goal(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            "app.services.bigset_remote_service.settings",
            type("S", (), {"BIGSET_IMPORT_DIR": str(tmp_path)})(),
        )
        path = persist_dataset_goal("Build hiring dataset for QA")
        assert path.exists()
        assert "QA" in path.read_text(encoding="utf-8")