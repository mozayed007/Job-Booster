"""Tests for VectorStore — Qdrant file-based, mocked client."""

from unittest.mock import MagicMock

import pytest

from app.services.embedding_service import EmbeddingService


@pytest.fixture(autouse=True)
def reset_singletons():
    from app.services.embedding_service import EmbeddingService as ES
    from app.services.vector_store import VectorStore as VS

    ES._instance = None
    VS._instance = None
    yield
    ES._instance = None
    VS._instance = None


@pytest.fixture
def mock_embedding_service():
    svc = EmbeddingService()
    svc._use_fallback = True
    return svc


@pytest.fixture
def mock_vector_store(mock_embedding_service, tmp_path):
    from app.services.vector_store import VectorStore

    mock_collection_info = MagicMock()
    mock_collection_info.points_count = 0

    mock_client = MagicMock()
    mock_client.collection_exists.return_value = True
    mock_client.get_collection.return_value = mock_collection_info
    mock_client.query_points.return_value = MagicMock(points=[])

    vs = VectorStore.__new__(VectorStore)
    vs._initialized = True
    vs._available = True
    vs._embedding_service = mock_embedding_service
    vs._persist_dir = tmp_path / "qdrant"
    vs._client = mock_client
    yield vs, mock_client


class TestVectorStoreInit:
    def test_not_available_when_qdrant_missing(self, mock_embedding_service, tmp_path):
        from app.services.vector_store import VectorStore

        vs = VectorStore.__new__(VectorStore)
        vs._initialized = True
        vs._available = False
        vs._embedding_service = mock_embedding_service
        vs._persist_dir = tmp_path / "nope"
        vs._client = None
        assert vs.is_available is False

    def test_available_with_qdrant(self, mock_vector_store):
        vs, _ = mock_vector_store
        assert vs.is_available is True


class TestAddDocument:
    @pytest.mark.asyncio
    async def test_add_document_calls_upsert(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        await vs.add_document("resumes", "r1", "resume text", {"name": "test"})
        mock_client.upsert.assert_called_once()
        call_args = mock_client.upsert.call_args
        assert call_args.kwargs["collection_name"] == "resumes"
        points = call_args.kwargs["points"]
        assert len(points) == 1
        assert points[0].payload["text"] == "resume text"
        assert points[0].payload["doc_id"] == "r1"
        assert points[0].payload["name"] == "test"
        assert len(points[0].vector) == 384

    @pytest.mark.asyncio
    async def test_add_document_no_metadata(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        await vs.add_document("jobs", "j1", "job text")
        call_args = mock_client.upsert.call_args
        point = call_args.kwargs["points"][0]
        assert point.payload["text"] == "job text"
        assert "doc_id" in point.payload


class TestSearch:
    @pytest.mark.asyncio
    async def test_search_empty_query(self, mock_vector_store):
        vs, _ = mock_vector_store
        results = await vs.search("resumes", "  ")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_empty_collection(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        mock_client.get_collection.return_value.points_count = 0
        results = await vs.search("resumes", "query")
        assert results == []

    @pytest.mark.asyncio
    async def test_search_returns_results(self, mock_vector_store):
        from qdrant_client.models import ScoredPoint

        vs, mock_client = mock_vector_store
        mock_client.get_collection.return_value.points_count = 2
        mock_client.query_points.return_value.points = [
            ScoredPoint(
                id="00000000-0000-0000-0000-000000000001",
                version=0,
                score=0.95,
                payload={"text": "doc1", "doc_id": "r1", "k": "v1"},
                vector=None,
            ),
            ScoredPoint(
                id="00000000-0000-0000-0000-000000000002",
                version=0,
                score=0.80,
                payload={"text": "doc2", "doc_id": "r2", "k": "v2"},
                vector=None,
            ),
        ]

        results = await vs.search("resumes", "test query", n_results=2)
        assert len(results) == 2
        assert results[0]["id"] == "r1"
        assert results[0]["text"] == "doc1"
        assert results[0]["score"] == 0.95
        assert results[0]["metadata"]["k"] == "v1"


class TestDeleteDocument:
    def test_delete_calls_client(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        vs.delete_document("resumes", "r1")
        mock_client.delete.assert_called_once()
        call_args = mock_client.delete.call_args
        assert call_args.kwargs["collection_name"] == "resumes"


class TestGetCollectionStats:
    def test_stats(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        mock_client.get_collection.return_value.points_count = 42
        stats = vs.get_collection_stats("resumes")
        assert stats == {"name": "resumes", "count": 42, "available": True}


class TestGetAllStats:
    def test_all_stats(self, mock_vector_store):
        vs, mock_client = mock_vector_store
        mock_client.get_collection.return_value.points_count = 5
        stats = vs.get_all_stats()
        assert stats["available"] is True
        assert "collections" in stats
        assert "resumes" in stats["collections"]
        assert stats["collections"]["resumes"]["count"] == 5
