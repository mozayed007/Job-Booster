"""Hybrid search over imported discovery jobs with profile reranking."""

from __future__ import annotations

from typing import Any

from loguru import logger
from sqlalchemy.orm import Session

from app.models.startup_model import UserProfile
from app.services.db_service import DatabaseService, get_db_session
from app.services.job_fit_service import rank_imported_jobs
from app.services.search_service import SearchService
from app.services.user_profile_service import load_user_profile
from app.services.vector_store import get_vector_store


async def search_imported_jobs(
    query: str,
    profile: UserProfile | None = None,
    *,
    limit: int = 10,
    db: Session | None = None,
) -> list[dict[str, Any]]:
    """Semantic + keyword search on jobs collection, reranked by profile fit."""
    profile = profile or load_user_profile()
    own_db = db is None
    if own_db:
        db = get_db_session()

    if not query.strip():
        try:
            return rank_imported_jobs(db, profile, limit=limit)
        finally:
            if own_db and db is not None:
                db.close()

    merged: dict[int, dict[str, Any]] = {}
    try:
        vs = get_vector_store()
        if vs.is_available and query.strip():
            svc = SearchService(
                vector_store=vs,
                db_service=DatabaseService(db),
            )
            vector_hits = await svc.hybrid_search(query, "jobs", limit * 2)
            for hit in vector_hits:
                meta = hit.get("metadata") or {}
                job_id = meta.get("job_id")
                if job_id is None and isinstance(hit.get("id"), str):
                    raw = hit["id"]
                    if raw.startswith("job_"):
                        try:
                            job_id = int(raw.split("_", 1)[1])
                        except ValueError:
                            job_id = None
                if job_id is None:
                    continue
                merged[int(job_id)] = {
                    "id": int(job_id),
                    "search_score": hit.get("score", 0.0),
                    "snippet": (hit.get("text") or "")[:400],
                }

        ranked = rank_imported_jobs(
            db,
            profile,
            limit=limit * 2,
            min_score=0.0 if profile.bigset.prefer_imported_jobs else profile.bigset.min_fit_score,
        )
        from app.models.db_models import JobPostingDB

        for row in ranked:
            jid = row["id"]
            job = db.get(JobPostingDB, jid)
            if not job:
                continue
            fit = row["fit_score"]
            entry = merged.get(jid, {"id": jid})
            entry.update({
                "title": row.get("title"),
                "company": row.get("company"),
                "location": row.get("location"),
                "source_url": row.get("source_url"),
                "fit_score": fit,
                "snippet": entry.get("snippet") or row.get("snippet"),
                "mapping_id": row.get("mapping_id"),
            })
            search_score = entry.get("search_score", 0.0)
            entry["combined_score"] = round(
                0.6 * fit + 0.4 * float(search_score),
                3,
            )
            merged[jid] = entry

        if not merged and query.strip():
            for row in ranked[:limit]:
                merged[row["id"]] = {**row, "combined_score": row["fit_score"]}

        results = sorted(
            merged.values(),
            key=lambda x: x.get("combined_score", x.get("fit_score", 0)),
            reverse=True,
        )
        return results[:limit]
    except Exception as e:
        logger.warning("search_imported_jobs failed: {}", e)
        if db is not None:
            return rank_imported_jobs(db, profile, limit=limit)
        return []
    finally:
        if own_db and db is not None:
            db.close()