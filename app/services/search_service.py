"""Hybrid search combining vector similarity + keyword matching."""

import re
from typing import Any, Optional

from loguru import logger

from app.services.db_service import DatabaseService
from app.services.vector_store import VectorStore, get_vector_store


class SearchService:
    """Hybrid search across resumes and jobs.

    Combines Qdrant vector similarity with keyword matching from the
    relational database, producing a merged and re-ranked result set.
    """

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        db_service: Optional[DatabaseService] = None,
    ):
        self.vector_store = vector_store or get_vector_store()
        self.db_service = db_service

    async def search_resumes(self, query: str, n_results: int = 10) -> list[dict[str, Any]]:
        """Search resumes by semantic similarity."""
        return await self.vector_store.search("resumes", query, n_results)

    async def search_jobs(self, query: str, n_results: int = 10) -> list[dict[str, Any]]:
        """Search jobs by semantic similarity."""
        return await self.vector_store.search("jobs", query, n_results)

    async def hybrid_search(
        self,
        query: str,
        collection: str,
        n_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Combine vector similarity with keyword matching.

        Fetches 2x from vector store, applies keyword boost, then re-ranks.
        """
        vector_results = await self.vector_store.search(collection, query, n_results * 2)
        keyword_results = self._keyword_search(collection, query)

        keyword_ids = {r["id"] for r in keyword_results}
        keywords = self._tokenize(query)

        seen: dict[str, dict[str, Any]] = {}

        for item in vector_results:
            doc_id = item["id"]
            distance = item.get("distance") or 1.0
            score = 1.0 - distance

            keyword_boost = 0.2 if doc_id in keyword_ids else 0.0
            text_lower = (item.get("text") or "").lower()
            term_boost = sum(0.05 for kw in keywords if kw in text_lower)

            item["score"] = min(score + keyword_boost + term_boost, 1.0)
            seen[doc_id] = item

        for item in keyword_results:
            doc_id = item["id"]
            if doc_id not in seen:
                text_lower = (item.get("text") or "").lower()
                term_boost = sum(0.05 for kw in keywords if kw in text_lower)
                item["score"] = 0.3 + term_boost
                seen[doc_id] = item

        ranked = sorted(seen.values(), key=lambda x: x.get("score", 0), reverse=True)
        return ranked[:n_results]

    async def index_resume(
        self, resume_id: int, text: str, metadata: Optional[dict[str, Any]] = None
    ):
        """Index a resume in the vector store."""
        meta = {"type": "resume", "resume_id": resume_id, **(metadata or {})}
        await self.vector_store.add_document("resumes", f"resume_{resume_id}", text, meta)
        logger.info(f"Indexed resume {resume_id}")

    async def index_job(self, job_id: int, text: str, metadata: Optional[dict[str, Any]] = None):
        """Index a job posting in the vector store."""
        meta = {"type": "job", "job_id": job_id, **(metadata or {})}
        await self.vector_store.add_document("jobs", f"job_{job_id}", text, meta)
        logger.info(f"Indexed job {job_id}")

    def _keyword_search(self, collection: str, query: str) -> list[dict[str, Any]]:
        """Keyword search against the relational DB (if available)."""
        if not self.db_service:
            return []

        try:
            table = "resumes" if collection == "resumes" else "job_postings"
            text_col = "raw_text"
            records = self.db_service.query_records(table, limit=50)

            keywords = self._tokenize(query)
            if not keywords:
                return []

            results = []
            for rec in records:
                raw = (rec.get(text_col) or "").lower()
                if any(kw in raw for kw in keywords):
                    results.append(
                        {
                            "id": f"{collection[:-1]}_{rec.get('id', '')}",
                            "text": rec.get(text_col, ""),
                            "metadata": {k: v for k, v in rec.items() if k != text_col},
                        }
                    )
            return results
        except Exception as e:
            logger.warning(f"Keyword search failed: {e}")
            return []

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        words = re.findall(r"\b\w{3,}\b", text.lower())
        stopwords = {
            "the",
            "and",
            "for",
            "are",
            "but",
            "not",
            "you",
            "all",
            "can",
            "has",
            "her",
            "was",
            "one",
            "our",
            "out",
            "this",
            "that",
            "with",
        }
        return [w for w in words if w not in stopwords]


def get_search_service(
    vector_store: Optional[VectorStore] = None,
    db_service: Optional[DatabaseService] = None,
) -> SearchService:
    """Create a SearchService instance."""
    return SearchService(vector_store=vector_store, db_service=db_service)
