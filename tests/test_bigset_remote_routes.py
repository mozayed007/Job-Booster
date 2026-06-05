"""Tests for BigSet remote discovery routes."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.bigset_remote_service import RemoteDatasetResult


@pytest.fixture
def client():
    return TestClient(app)


class TestBigSetRemoteRoutes:
    def test_remote_status(self, client, auth_token):
        resp = client.get(
            "/api/discovery/bigset/remote/status",
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["success"] is True
        assert "remote_enabled" in data
        assert "tinyfish_configured" in data

    @patch(
        "app.api.discovery_routes.maybe_request_dataset_build",
        new_callable=AsyncMock,
    )
    def test_remote_trigger(self, mock_build, client, auth_token):
        mock_build.return_value = RemoteDatasetResult(
            goal="test goal",
            attempted=False,
            message="disabled",
        )
        resp = client.post(
            "/api/discovery/bigset/remote/trigger",
            json={"force": False},
            headers={"Authorization": f"Bearer {auth_token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["success"] is True
        mock_build.assert_awaited_once()