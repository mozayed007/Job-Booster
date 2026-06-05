"""Tests for discovery sync agent."""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.agents.base_agent import AgentConfig
from app.agents.discovery_sync import DiscoverySyncAgent
from app.models.db_models import Base
from app.pipelines.state import PipelineState


@pytest.fixture
def agent(tmp_path):
    config = AgentConfig(name="Discovery Sync", description="test")
    return DiscoverySyncAgent(config, tmp_path)


class TestDiscoverySyncAgent:
    @pytest.mark.asyncio
    async def test_execute_writes_artifacts(self, agent, tmp_path, monkeypatch):
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)

        async def fake_import(*args, **kwargs):
            from app.services.bigset_import_service import BigSetImportResult

            return [BigSetImportResult(mapping_id="test", stored=1, success=True)]

        monkeypatch.setattr(
            "app.agents.discovery_sync.import_changed_files_in_dir",
            fake_import,
        )
        async def fake_remote(*args, **kwargs):
            from app.services.bigset_remote_service import RemoteDatasetResult

            return RemoteDatasetResult(goal="test goal")

        monkeypatch.setattr(
            "app.agents.discovery_sync.maybe_request_dataset_build",
            fake_remote,
        )

        state = PipelineState(pipeline_name="test")
        await agent.execute(state)
        assert "discovery_sync" in state.artifacts
        assert state.artifacts["discovery_sync"]["import_files"] == 1