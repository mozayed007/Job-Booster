"""Qdrant file-based vector storage for document embeddings."""

import uuid
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from app.services.embedding_service import EmbeddingService, get_embedding_service

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        FieldCondition,
        Filter,
        MatchValue,
        PointStruct,
        VectorParams,
    )

    QDRANT_AVAILABLE = True
except ImportError:
    QDRANT_AVAILABLE = False
    logger.warning("qdrant-client not installed — vector store will be unavailable")


QDRANT_PATH = Path("data") / "qdrant"
COLLECTION_NAMES = ("resumes", "jobs", "cover_letters")
VECTOR_DIM = 384


class VectorStore:
    """Qdrant file-based vector store with pluggable embedding service.

    Manages collections for resumes, jobs, and cover letters.
    Falls back gracefully when qdrant-client is not installed.
    """

    _instance: Optional["VectorStore"] = None

    def __new__(cls, *args, **kwargs) -> "VectorStore":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(
        self,
        embedding_service: Optional[EmbeddingService] = None,
        persist_dir: Optional[Path] = None,
    ):
        if self._initialized:
            return
        self._initialized = True
        self._available = QDRANT_AVAILABLE
        self._embedding_service = embedding_service or get_embedding_service()
        self._persist_dir = persist_dir or QDRANT_PATH
        self._client: Optional[Any] = None

        if self._available:
            self._init_client()

    def _init_client(self):
        try:
            self._persist_dir.mkdir(parents=True, exist_ok=True)
            self._client = QdrantClient(path=str(self._persist_dir))
            for name in COLLECTION_NAMES:
                if not self._client.collection_exists(name):
                    self._client.create_collection(
                        collection_name=name,
                        vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
                    )
            logger.info(f"VectorStore: initialized at {self._persist_dir}")
        except Exception as e:
            logger.error(f"VectorStore init failed: {e}")
            self._available = False

    def _ensure_collection(self, name: str):
        if not self._available or self._client is None:
            raise RuntimeError("VectorStore unavailable")
        if not self._client.collection_exists(name):
            self._client.create_collection(
                collection_name=name,
                vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
            )

    async def add_document(
        self,
        collection: str,
        doc_id: str,
        text: str,
        metadata: Optional[dict[str, Any]] = None,
    ):
        """Add a document to a collection."""
        self._ensure_collection(collection)
        embedding = await self._embedding_service.embed_text(text)
        point = PointStruct(
            id=str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id)),
            vector=embedding,
            payload={"text": text, "doc_id": doc_id, **(metadata or {})},
        )
        self._client.upsert(collection_name=collection, points=[point])
        logger.debug(f"VectorStore: upserted {doc_id} into {collection}")

    async def search(
        self,
        collection: str,
        query_text: str,
        n_results: int = 5,
        filter_by: Optional[dict[str, str]] = None,
    ) -> list[dict[str, Any]]:
        """Search a collection by query text."""
        if not query_text.strip():
            return []

        if not self._available or self._client is None:
            return []

        if not self._client.collection_exists(collection):
            return []

        info = self._client.get_collection(collection)
        if info.points_count == 0:
            return []

        embedding = await self._embedding_service.embed_text(query_text)

        query_filter = None
        if filter_by:
            must = [FieldCondition(key=k, match=MatchValue(value=v)) for k, v in filter_by.items()]
            query_filter = Filter(must=must)

        results = self._client.query_points(
            collection_name=collection,
            query=embedding,
            limit=n_results,
            query_filter=query_filter,
            with_payload=True,
        )

        items = []
        for hit in results.points:
            payload = hit.payload or {}
            items.append(
                {
                    "id": payload.get("doc_id", hit.id),
                    "text": payload.get("text", ""),
                    "metadata": {k: v for k, v in payload.items() if k not in ("text", "doc_id")},
                    "score": hit.score,
                }
            )
        return items

    def delete_document(self, collection: str, doc_id: str):
        """Delete a document from a collection."""
        self._ensure_collection(collection)
        point_id = str(uuid.uuid5(uuid.NAMESPACE_URL, doc_id))
        self._client.delete(
            collection_name=collection,
            points_selector=[point_id],
        )
        logger.debug(f"VectorStore: deleted {doc_id} from {collection}")

    def get_collection_stats(self, collection: str) -> dict[str, Any]:
        """Get statistics for a collection."""
        if not self._available or self._client is None:
            return {"name": collection, "count": 0, "available": False}
        if not self._client.collection_exists(collection):
            return {"name": collection, "count": 0, "available": False}
        info = self._client.get_collection(collection)
        return {
            "name": collection,
            "count": info.points_count,
            "available": True,
        }

    def get_all_stats(self) -> dict[str, Any]:
        """Get stats for all collections."""
        stats = {}
        for name in COLLECTION_NAMES:
            try:
                stats[name] = self.get_collection_stats(name)
            except Exception:
                stats[name] = {"name": name, "count": 0, "available": False}
        return {
            "available": self._available,
            "persist_dir": str(self._persist_dir),
            "collections": stats,
        }

    @property
    def is_available(self) -> bool:
        return self._available


def get_vector_store() -> VectorStore:
    """Get the singleton VectorStore instance."""
    return VectorStore()
