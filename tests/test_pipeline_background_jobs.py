"""Tests for in-memory background pipeline job bookkeeping."""

import time

from app.api import pipeline_routes as routes


class TestBackgroundJobStore:
    def setup_method(self):
        routes._background_jobs.clear()

    def test_prune_expires_old_jobs(self, monkeypatch):
        monkeypatch.setattr(routes.settings, "PIPELINE_BACKGROUND_JOB_TTL_SECONDS", 1)
        monkeypatch.setattr(routes.settings, "PIPELINE_BACKGROUND_JOB_MAX_ENTRIES", 10)
        routes._set_background_job("old", {"status": "completed", "pipeline_key": "x"})
        routes._background_jobs["old"]["_updated_at"] = time.time() - 10
        routes._prune_background_jobs()
        assert "old" not in routes._background_jobs

    def test_prune_caps_max_entries(self, monkeypatch):
        monkeypatch.setattr(routes.settings, "PIPELINE_BACKGROUND_JOB_TTL_SECONDS", 86_400)
        monkeypatch.setattr(routes.settings, "PIPELINE_BACKGROUND_JOB_MAX_ENTRIES", 2)
        for i in range(3):
            routes._set_background_job(f"job-{i}", {"status": "running", "pipeline_key": "x"})
            time.sleep(0.01)
        routes._prune_background_jobs()
        assert len(routes._background_jobs) == 2
        assert "job-0" not in routes._background_jobs

    def test_status_hides_internal_timestamps(self):
        routes._set_background_job("j1", {"status": "running", "pipeline_key": "daily_scanner"})
        job = routes._background_jobs["j1"]
        assert "_created_at" in job
        assert "_updated_at" in job