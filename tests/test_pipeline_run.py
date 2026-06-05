"""Tests for pipeline list and run API."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.pipelines.state import PipelineState


@pytest.fixture
def client():
    return TestClient(app)


class TestPipelineRunAPI:
    def test_pipeline_list(self, client):
        resp = client.get("/api/pipeline/list")
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        keys = {p["key"] for p in data["pipelines"]}
        assert "discovery_sync_only" in keys
        assert "daily_scanner" in keys

    def test_pipeline_run_requires_auth(self, client):
        resp = client.post(
            "/api/pipeline/run",
            json={"pipeline_key": "discovery_sync_only"},
        )
        assert resp.status_code == 401

    @patch("app.api.pipeline_routes.run_pipeline", new_callable=AsyncMock)
    def test_pipeline_run_sync(self, mock_run, client, auth_token):
        state = PipelineState(pipeline_name="Discovery Sync Only")
        state.artifacts["discovery_sync"] = {"import_files": 0, "jobs_stored": 0}
        mock_run.return_value = state

        resp = client.post(
            "/api/pipeline/run",
            json={"pipeline_key": "discovery_sync_only", "inputs": {}},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["success"] is True
        assert body["status"] == "completed"
        assert "discovery_sync" in body["data"]["artifacts"]
        mock_run.assert_awaited_once()