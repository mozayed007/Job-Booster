"""Shared job posting deduplication keys and lookups."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.db_models import JobPostingDB


def job_dedupe_key(
    company: str,
    title: str,
    url: str,
    *,
    company_stub: bool = False,
) -> str:
    """Stable key for import/scrape dedupe. Company stubs use fixed stub title only."""
    if url:
        return f"url:{url.lower()}"
    if company_stub:
        return f"stub:{company.lower()}|{title.lower()}"
    return f"ct:{company.lower()}|{title.lower()}"


def find_existing_job(
    db: Session,
    company: str,
    title: str,
    url: str,
    *,
    company_stub: bool = False,
) -> JobPostingDB | None:
    """Find an existing posting matching the dedupe key."""
    url = (url or "").strip()
    company = (company or "").strip()
    title = (title or "").strip()
    if url:
        return db.query(JobPostingDB).filter(JobPostingDB.source_url == url).first()
    if company_stub:
        stub_key = title.lower()
        rows = db.query(JobPostingDB).filter(JobPostingDB.company == company).all()
        for row in rows:
            row_title = (row.title or "").strip()
            if row_title.lower() == stub_key or row_title.lower().startswith(f"{stub_key} ("):
                return row
        return None
    return (
        db.query(JobPostingDB)
        .filter(JobPostingDB.company == company, JobPostingDB.title == title)
        .first()
    )


def load_dedupe_keys(
    db: Session,
    companies: set[str] | None = None,
) -> set[str]:
    """Load dedupe keys for existing jobs, optionally scoped to companies."""
    q = db.query(
        JobPostingDB.company,
        JobPostingDB.title,
        JobPostingDB.source_url,
    )
    if companies:
        q = q.filter(JobPostingDB.company.in_(list(companies)))
    keys: set[str] = set()
    for company, title, source_url in q.all():
        url = (source_url or "").strip()
        co = (company or "").strip()
        ti = (title or "").strip()
        if url:
            keys.add(job_dedupe_key(co, ti, url))
        else:
            keys.add(job_dedupe_key(co, ti, url))
    return keys
