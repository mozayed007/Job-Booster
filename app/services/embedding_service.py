"""Embedding generation service using LiteLLM with hash-based fallback."""

import hashlib
import os
from typing import Optional

from loguru import logger

from app.core.model_registry import get_registry

EMBEDDING_MODEL_ENV = "EMBEDDING_MODEL"
DEFAULT_FALLBACK_DIM = 384


class EmbeddingService:
    """Singleton service for generating text embeddings.

    Uses LiteLLM aembedding() for async embedding generation across multiple
    providers (OpenAI, Google, Cohere, etc.). Falls back to a deterministic
    hash-based embedding when no provider is available (testing/dev).
    """

    _instance: Optional["EmbeddingService"] = None

    def __new__(cls) -> "EmbeddingService":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._model = self._resolve_model()
        self._use_fallback = False
        self._fallback_dim = DEFAULT_FALLBACK_DIM
        logger.info(f"EmbeddingService: model={self._model}")

    def _resolve_model(self) -> str:
        env_model = os.getenv(EMBEDDING_MODEL_ENV)
        if env_model:
            return env_model
        try:
            return get_registry().get_model_string()
        except Exception:
            return "openai:text-embedding-3-small"

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text."""
        if not text or not text.strip():
            return [0.0] * self._fallback_dim

        if self._use_fallback:
            return self._hash_embed(text)

        try:
            import litellm

            response = await litellm.aembedding(model=self._model, input=[text])
            return response.data[0]["embedding"]
        except Exception as e:
            logger.warning(f"LiteLLM embedding failed, using hash fallback: {e}")
            self._use_fallback = True
            return self._hash_embed(text)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """Generate embedding vectors for a batch of texts."""
        if not texts:
            return []

        cleaned = [t if t and t.strip() else "" for t in texts]

        if self._use_fallback:
            return [self._hash_embed(t) if t else [0.0] * self._fallback_dim for t in cleaned]

        try:
            import litellm

            non_empty = [t for t in cleaned if t]
            if not non_empty:
                return [[0.0] * self._fallback_dim for _ in cleaned]

            response = await litellm.aembedding(model=self._model, input=non_empty)
            embeddings = [item["embedding"] for item in response.data]

            result = []
            idx = 0
            for t in cleaned:
                if t:
                    result.append(embeddings[idx])
                    idx += 1
                else:
                    result.append([0.0] * self._fallback_dim)
            return result
        except Exception as e:
            logger.warning(f"LiteLLM batch embedding failed, using hash fallback: {e}")
            self._use_fallback = True
            return [self._hash_embed(t) if t else [0.0] * self._fallback_dim for t in cleaned]

    @staticmethod
    def _hash_embed(text: str, dim: int = DEFAULT_FALLBACK_DIM) -> list[float]:
        """Deterministic hash-based embedding for fallback/testing."""
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        values = []
        for i in range(dim):
            hex_pair = digest[(i * 2) % len(digest) : (i * 2 + 2) % len(digest)]
            if len(hex_pair) < 2:
                hex_pair = digest[:2]
            val = (int(hex_pair, 16) / 255.0) * 2.0 - 1.0
            values.append(val)
        norm = (sum(v * v for v in values) ** 0.5) or 1.0
        return [v / norm for v in values]

    @property
    def model(self) -> str:
        return self._model

    @property
    def is_fallback(self) -> bool:
        return self._use_fallback


def get_embedding_service() -> EmbeddingService:
    """Get the singleton EmbeddingService instance."""
    return EmbeddingService()
