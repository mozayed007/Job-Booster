"""Score and rank imported job postings against user profile preferences."""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.models.db_models import JobPostingDB
from app.models.startup_model import UserProfile
from app.services.bigset_import_service import BIGSET_SOURCE, _score_text_for_skills


def _job_text_blob(job: JobPostingDB) -> str:
    parts = [
        job.title or "",
        job.company or "",
        job.location or "",
        job.raw_text or "",
        job.source_url or "",
    ]
    parsed = job.content_json if isinstance(job.content_json, dict) else {}
    parts.append(str(parsed.get("mapping_id", "")))
    return " ".join(parts)


def score_job_against_profile(job: JobPostingDB, profile: UserProfile) -> float:
    """Return 0-1 fit score from keyword overlap and location/category hints."""
    blob = _job_text_blob(job).lower()
    keywords = [
        k.strip()
        for k in (
            list(profile.skills)
            + list(profile.target_role_keywords)
            + list(profile.preferred_categories)
        )
        if k and k.strip()
    ]
    if not keywords:
        return 0.5

    skill_hits = _score_text_for_skills(blob, keywords)
    max_possible = max(len(keywords), 1)
    base = min(skill_hits / max_possible, 1.0)

    loc_bonus = 0.0
    for loc in profile.preferred_locations:
        if loc.strip() and loc.lower() in blob:
            loc_bonus = 0.15
            break

    return min(base + loc_bonus, 1.0)


def _is_imported_job(job: JobPostingDB, source: str) -> bool:
    parsed = job.content_json if isinstance(job.content_json, dict) else {}
    return parsed.get("source") == source


def rank_imported_jobs(
    db: Session,
    profile: UserProfile,
    *,
    source: str = BIGSET_SOURCE,
    limit: int = 20,
    min_score: float | None = None,
) -> list[dict[str, Any]]:
    """Rank imported postings by profile fit."""
    if min_score is None:
        min_score = profile.bigset.min_fit_score

    rows = db.query(JobPostingDB).order_by(JobPostingDB.id.desc()).limit(500).all()
    scored: list[tuple[float, JobPostingDB]] = []
    for job in rows:
        if not _is_imported_job(job, source):
            continue
        fit = score_job_against_profile(job, profile)
        if fit < min_score:
            continue
        scored.append((fit, job))

    scored.sort(key=lambda x: (-x[0], x[1].id or 0))
    out: list[dict[str, Any]] = []
    for fit, job in scored[:limit]:
        out.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "source_url": job.source_url,
            "fit_score": round(fit, 3),
            "snippet": (job.raw_text or "")[:400],
            "mapping_id": (job.content_json or {}).get("mapping_id")
            if isinstance(job.content_json, dict)
            else None,
        })
    return out


def jobs_for_company(
    db: Session,
    company: str,
    *,
    source: str = BIGSET_SOURCE,
    limit: int = 5,
) -> list[JobPostingDB]:
    """Imported postings for one company (career-page hints)."""
    rows = (
        db.query(JobPostingDB)
        .filter(JobPostingDB.company == company)
        .order_by(JobPostingDB.id.desc())
        .limit(50)
        .all()
    )
    return [j for j in rows if _is_imported_job(j, source)][:limit]