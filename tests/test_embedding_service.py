"""Tests for EmbeddingService — mock-based, no actual API calls."""

from unittest.mock import AsyncMock, patch

import pytest

from app.services.embedding_service import EmbeddingService, get_embedding_service


@pytest.fixture(autouse=True)
def reset_singleton():
    """Reset singleton between tests."""
    EmbeddingService._instance = None
    yield
    EmbeddingService._instance = None


class TestHashEmbed:
    def test_deterministic(self):
        vec1 = EmbeddingService._hash_embed("hello world")
        vec2 = EmbeddingService._hash_embed("hello world")
        assert vec1 == vec2

    def test_different_inputs_differ(self):
        vec1 = EmbeddingService._hash_embed("hello")
        vec2 = EmbeddingService._hash_embed("world")
        assert vec1 != vec2

    def test_output_length(self):
        vec = EmbeddingService._hash_embed("test")
        assert len(vec) == 384

    def test_normalized(self):
        vec = EmbeddingService._hash_embed("normalize me")
        norm = sum(v * v for v in vec) ** 0.5
        assert abs(norm - 1.0) < 1e-6

    def test_empty_string(self):
        vec = EmbeddingService._hash_embed("")
        assert len(vec) == 384


class TestEmbeddingServiceSingleton:
    def test_singleton(self):
        svc1 = EmbeddingService()
        svc2 = EmbeddingService()
        assert svc1 is svc2

    def test_get_embedding_service(self):
        svc = get_embedding_service()
        assert isinstance(svc, EmbeddingService)


class TestEmbedText:
    @pytest.mark.asyncio
    async def test_empty_text_returns_zeros(self):
        svc = EmbeddingService()
        vec = await svc.embed_text("")
        assert len(vec) == 384
        assert all(v == 0.0 for v in vec)

    @pytest.mark.asyncio
    async def test_whitespace_text_returns_zeros(self):
        svc = EmbeddingService()
        vec = await svc.embed_text("   ")
        assert all(v == 0.0 for v in vec)

    @pytest.mark.asyncio
    async def test_litellm_success(self):
        mock_response = AsyncMock()
        mock_response.data = [{"embedding": [0.1, 0.2, 0.3]}]

        svc = EmbeddingService()

        with patch("app.services.embedding_service.litellm", create=True) as mock_litellm:
            mock_litellm.aembedding = AsyncMock(return_value=mock_response)
            svc._use_fallback = False

            with patch.dict("sys.modules", {"litellm": mock_litellm}):
                vec = await svc.embed_text("hello")
                assert vec == [0.1, 0.2, 0.3]

    @pytest.mark.asyncio
    async def test_litellm_failure_falls_back(self):
        svc = EmbeddingService()
        svc._use_fallback = False

        with patch.dict("sys.modules", {"litellm": None}):
            vec = await svc.embed_text("test fallback")
            assert len(vec) == 384
            assert svc._use_fallback is True

    @pytest.mark.asyncio
    async def test_fallback_mode_direct(self):
        svc = EmbeddingService()
        svc._use_fallback = True
        vec = await svc.embed_text("test")
        expected = EmbeddingService._hash_embed("test")
        assert vec == expected


class TestEmbedBatch:
    @pytest.mark.asyncio
    async def test_empty_batch(self):
        svc = EmbeddingService()
        result = await svc.embed_batch([])
        assert result == []

    @pytest.mark.asyncio
    async def test_batch_with_fallback(self):
        svc = EmbeddingService()
        svc._use_fallback = True
        texts = ["hello", "world", ""]
        result = await svc.embed_batch(texts)
        assert len(result) == 3
        assert result[0] == EmbeddingService._hash_embed("hello")
        assert result[1] == EmbeddingService._hash_embed("world")
        assert all(v == 0.0 for v in result[2])

    @pytest.mark.asyncio
    async def test_batch_litellm_success(self):
        mock_response = AsyncMock()
        mock_response.data = [
            {"embedding": [0.1, 0.2]},
            {"embedding": [0.3, 0.4]},
        ]

        svc = EmbeddingService()
        svc._use_fallback = False

        mock_litellm = AsyncMock()
        mock_litellm.aembedding = AsyncMock(return_value=mock_response)

        with patch.dict("sys.modules", {"litellm": mock_litellm}):
            result = await svc.embed_batch(["a", "b"])
            assert len(result) == 2
            assert result[0] == [0.1, 0.2]
            assert result[1] == [0.3, 0.4]

    @pytest.mark.asyncio
    async def test_batch_litellm_failure_falls_back(self):
        svc = EmbeddingService()
        svc._use_fallback = False

        with patch.dict("sys.modules", {"litellm": None}):
            result = await svc.embed_batch(["a", "b"])
            assert len(result) == 2
            assert svc._use_fallback is True
            assert result[0] == EmbeddingService._hash_embed("a")


class TestProperties:
    def test_model_property(self):
        svc = EmbeddingService()
        assert isinstance(svc.model, str)
        assert len(svc.model) > 0

    def test_is_fallback_default(self):
        svc = EmbeddingService()
        assert svc.is_fallback is False
