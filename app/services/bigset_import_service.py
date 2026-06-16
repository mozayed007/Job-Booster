"""Import BigSet CSV exports into Job Booster discovery storage."""

from __future__ import annotations

import contextlib
import csv
import io
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

import yaml
from loguru import logger
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.db_models import JobPostingDB, StartupDB
from app.models.startup_model import Startup
from app.services.db_service import DatabaseService
from app.services.job_dedupe import find_existing_job, job_dedupe_key, load_dedupe_keys
from app.services.search_service import SearchService
from app.services.vector_store import get_vector_store

BIGSET_CATEGORY = "BigSet"
BIGSET_SOURCE = "bigset"
_MAPPINGS_PATH = Path(__file__).resolve().parents[2] / "config" / "bigset_mappings.yaml"


class BigSetImportResult(BaseModel):
    """Outcome of a BigSet file import."""

    success: bool = True
    mapping_id: str = ""
    stored: int = 0
    startups_upserted: int = 0
    skipped_duplicates: int = 0
    indexed: int = 0
    errors: list[str] = Field(default_factory=list)


@dataclass
class MappingProfile:
    """Column mapping for one BigSet dataset shape."""

    mapping_id: str
    level: Literal["company", "job"]
    columns: dict[str, str]
    open_roles_column: str | None = None
    company_stub_title: str = "Open roles"
    filename_patterns: list[str] = field(default_factory=list)


def load_mappings(path: Path | None = None) -> dict[str, MappingProfile]:
    """Load mapping profiles from YAML."""
    path = path or _MAPPINGS_PATH
    if not path.exists():
        logger.warning("BigSet mappings file not found: {}", path)
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    profiles: dict[str, MappingProfile] = {}
    for mapping_id, spec in raw.items():
        if not isinstance(spec, dict):
            continue
        profiles[mapping_id] = MappingProfile(
            mapping_id=mapping_id,
            level=spec.get("level", "job"),
            columns=spec.get("columns") or {},
            open_roles_column=spec.get("open_roles_column"),
            company_stub_title=str(spec.get("company_stub_title") or "Open roles"),
            filename_patterns=list(spec.get("filename_patterns") or []),
        )
    return profiles


def list_mapping_ids() -> list[dict[str, Any]]:
    """Return mapping metadata for API discovery."""
    return [
        {
            "id": p.mapping_id,
            "level": p.level,
            "columns": p.columns,
            "filename_patterns": p.filename_patterns,
        }
        for p in load_mappings().values()
    ]


def preview_import(
    content: bytes,
    filename: str,
    mapping_id: str | None = None,
) -> dict[str, Any]:
    """Validate file headers against a mapping without writing to the database."""
    mappings = load_mappings()
    mid = resolve_mapping_id(filename, mapping_id, mappings)
    if mid not in mappings:
        return {
            "success": False,
            "resolved_mapping": mid,
            "errors": [f"Unknown mapping_id: {mid}"],
        }

    profile = mappings[mid]
    try:
        rows = parse_tabular_file(content, filename)
    except Exception as e:
        return {
            "success": False,
            "resolved_mapping": mid,
            "errors": [str(e)],
        }

    if not rows:
        return {
            "success": False,
            "resolved_mapping": mid,
            "errors": ["No rows found in file"],
        }

    file_headers = list(rows[0].keys())
    expected = list(profile.columns.values())
    if profile.open_roles_column:
        expected.append(profile.open_roles_column)
    expected_set = {h.strip() for h in expected if h}
    file_set = {h.strip() for h in file_headers if h}
    matched = sorted(expected_set & file_set)
    missing = sorted(expected_set - file_set)
    extra = sorted(file_set - expected_set)
    can_import = len(missing) == 0

    return {
        "success": True,
        "resolved_mapping": mid,
        "level": profile.level,
        "row_count": len(rows),
        "file_headers": file_headers,
        "expected_columns": expected,
        "matched": matched,
        "missing": missing,
        "extra": extra,
        "can_import": can_import,
        "sample_rows": rows[:5],
    }


def resolve_mapping_id(
    filename: str,
    explicit: str | None = None,
    mappings: dict[str, MappingProfile] | None = None,
) -> str:
    """Pick mapping from explicit id, filename patterns, or default setting."""
    if explicit:
        return explicit
    mappings = mappings or load_mappings()
    lower = filename.lower()
    for mid, profile in mappings.items():
        for pattern in profile.filename_patterns:
            if pattern.lower() in lower:
                return mid
    default = getattr(settings, "BIGSET_DEFAULT_MAPPING", "generic_job_listing")
    if default in mappings:
        return default
    return next(iter(mappings), default)


def normalize_url(url: str | None) -> str:
    """Ensure website/job URLs have a scheme."""
    if not url or not str(url).strip():
        return ""
    u = str(url).strip()
    if u.startswith(("http://", "https://")):
        return u
    return f"https://{u}"


def parse_tabular_file(content: bytes, filename: str) -> list[dict[str, str]]:
    """Parse CSV (and XLSX when openpyxl is installed) into row dicts."""
    lower = filename.lower()
    if lower.endswith(".xlsx") or lower.endswith(".xlsm"):
        try:
            import openpyxl
        except ImportError as e:
            raise ValueError(
                "XLSX import requires openpyxl. Install it or export CSV from BigSet."
            ) from e
        wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
        ws = wb.active
        if ws is None:
            raise ValueError("Workbook has no active worksheet")
        rows_iter = ws.iter_rows(values_only=True)
        headers = [str(c or "").strip() for c in next(rows_iter, [])]
        rows: list[dict[str, str]] = []
        for row in rows_iter:
            rows.append(
                {
                    headers[i]: str(row[i] if i < len(row) and row[i] is not None else "")
                    for i in range(len(headers))
                }
            )
        wb.close()
        return rows

    text = content.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return [{k: (v or "").strip() for k, v in row.items()} for row in reader]


def _row_value(row: dict[str, str], header: str | None) -> str:
    if not header:
        return ""
    return (row.get(header) or "").strip()


def _mapped_fields(row: dict[str, str], profile: MappingProfile) -> dict[str, str]:
    return {internal: _row_value(row, header) for internal, header in profile.columns.items()}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


@contextlib.contextmanager
def _acquire_folder_import_lock(directory: Path):
    """Exclusive lock so only one process imports from the watch folder at a time."""
    directory.mkdir(parents=True, exist_ok=True)
    lock_path = directory / ".bigset_import.lock"
    fd: int | None = None
    acquired = False
    try:
        fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        acquired = True
        yield True
    except FileExistsError:
        yield False
    finally:
        if fd is not None:
            os.close(fd)
        if acquired:
            try:
                lock_path.unlink(missing_ok=True)
            except OSError:
                logger.warning("Could not remove BigSet import lock {}", lock_path)


class BigSetImportService:
    """Parse BigSet exports and persist into SQLite + optional Qdrant index."""

    def __init__(self, db: Session):
        self.db = db
        self.db_svc = DatabaseService(db)

    def upsert_startup(
        self,
        *,
        name: str,
        website: str | None,
        city: str,
        funding_round: str | None,
    ) -> tuple[int, bool]:
        """Insert or update a startup row. Returns (id, created)."""
        existing = self.db.query(StartupDB).filter(StartupDB.name == name).first()
        if existing:
            if website:
                existing.website = website
            if city:
                existing.city = city
            if funding_round:
                existing.funding_round = funding_round
            existing.category = BIGSET_CATEGORY
            return existing.id, False
        row = StartupDB(
            name=name,
            city=city or "Unknown",
            category=BIGSET_CATEGORY,
            website=website,
            funding_round=funding_round,
            last_scanned=None,
        )
        self.db.add(row)
        self.db.flush()
        return row.id, True

    def _refresh_existing_job(
        self,
        existing: JobPostingDB,
        *,
        display_title: str,
        location: str,
        raw_text: str,
        parsed_data: dict[str, Any],
    ) -> None:
        existing.title = display_title
        existing.location = location
        existing.raw_text = raw_text
        existing.content_json = parsed_data

    async def import_file(
        self,
        content: bytes,
        filename: str,
        mapping_id: str | None = None,
    ) -> BigSetImportResult:
        """Import one BigSet export file."""
        mappings = load_mappings()
        mid = resolve_mapping_id(filename, mapping_id, mappings)
        if mid not in mappings:
            return BigSetImportResult(
                success=False,
                mapping_id=mid,
                errors=[f"Unknown mapping_id: {mid}"],
            )
        profile = mappings[mid]

        try:
            rows = parse_tabular_file(content, filename)
        except Exception as e:
            return BigSetImportResult(
                success=False,
                mapping_id=mid,
                errors=[str(e)],
            )

        if not rows:
            return BigSetImportResult(
                success=False,
                mapping_id=mid,
                errors=["No rows found in file"],
            )

        companies_in_file: set[str] = set()
        for row in rows:
            fields = _mapped_fields(row, profile)
            if profile.level == "company":
                if fields.get("company"):
                    companies_in_file.add(fields["company"])
            elif fields.get("company"):
                companies_in_file.add(fields["company"])

        seen_jobs = load_dedupe_keys(self.db, companies_in_file or None)
        job_dicts: list[dict[str, Any]] = []
        startups_upserted = 0
        skipped = 0
        updated = 0

        try:
            for row in rows:
                fields = _mapped_fields(row, profile)
                if profile.level == "company":
                    company = fields.get("company", "")
                    if not company:
                        skipped += 1
                        continue
                    website = normalize_url(fields.get("website"))
                    location = fields.get("location", "Unknown")
                    funding = fields.get("funding_round") or None
                    _, created = self.upsert_startup(
                        name=company,
                        website=website or None,
                        city=location,
                        funding_round=funding,
                    )
                    if created:
                        startups_upserted += 1

                    open_roles = _row_value(row, profile.open_roles_column)
                    desc = fields.get("description", "")
                    stub = profile.company_stub_title
                    display_title = stub
                    if open_roles:
                        display_title = f"{stub} ({open_roles} listings)"
                    raw = (
                        f"{desc}. Stage: {funding or 'n/a'}. "
                        f"Open roles: {open_roles or 'n/a'}. source:{BIGSET_SOURCE}"
                    )
                    key = job_dedupe_key(company, stub, website, company_stub=True)
                    parsed = {"source": BIGSET_SOURCE, "mapping_id": mid}
                    if key in seen_jobs:
                        existing = find_existing_job(
                            self.db,
                            company,
                            stub,
                            website,
                            company_stub=True,
                        )
                        if existing:
                            self._refresh_existing_job(
                                existing,
                                display_title=display_title,
                                location=location,
                                raw_text=f"{display_title} at {company}. {raw}",
                                parsed_data=parsed,
                            )
                            updated += 1
                        else:
                            skipped += 1
                        continue
                    seen_jobs.add(key)
                    job_dicts.append(
                        {
                            "title": display_title,
                            "company": company,
                            "location": location,
                            "raw_text": f"{display_title} at {company}. {raw}",
                            "source_url": website or None,
                            "parsed_data": parsed,
                        }
                    )
                else:
                    title = fields.get("title", "")
                    company = fields.get("company", "")
                    if not title or not company:
                        skipped += 1
                        continue
                    url = normalize_url(fields.get("url"))
                    location = fields.get("location", "")
                    desc = fields.get("description", "")
                    key = job_dedupe_key(company, title, url)
                    if key in seen_jobs:
                        existing = find_existing_job(self.db, company, title, url)
                        if existing:
                            self._refresh_existing_job(
                                existing,
                                display_title=title,
                                location=location,
                                raw_text=(f"{title} at {company}. {desc} source:{BIGSET_SOURCE}"),
                                parsed_data={
                                    "source": BIGSET_SOURCE,
                                    "mapping_id": mid,
                                },
                            )
                            updated += 1
                        else:
                            skipped += 1
                        continue
                    seen_jobs.add(key)
                    job_dicts.append(
                        {
                            "title": title,
                            "company": company,
                            "location": location,
                            "raw_text": (f"{title} at {company}. {desc} source:{BIGSET_SOURCE}"),
                            "source_url": url or None,
                            "parsed_data": {
                                "source": BIGSET_SOURCE,
                                "mapping_id": mid,
                            },
                        }
                    )

            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        inserted_ids = self.db_svc.store_scraped_jobs_batch(job_dicts, dedupe=True)
        stored = len([i for i in inserted_ids if i is not None])
        indexed = 0
        try:
            vs = get_vector_store()
            if vs.is_available and any(i is not None for i in inserted_ids):
                search_svc = SearchService(vector_store=vs)
                for job_data, job_id in zip(job_dicts, inserted_ids):
                    if job_id is None:
                        continue
                    await search_svc.index_job(job_id, job_data["raw_text"][:5000])
                    indexed += 1
        except Exception as e:
            logger.warning("BigSet vector indexing failed (non-fatal): {}", e)

        return BigSetImportResult(
            mapping_id=mid,
            stored=stored,
            startups_upserted=startups_upserted,
            skipped_duplicates=skipped + updated,
            indexed=indexed,
        )


def list_imported_startups(db: Session) -> list[Startup]:
    """Startups previously imported from BigSet."""
    rows = (
        db.query(StartupDB)
        .filter(StartupDB.category == BIGSET_CATEGORY)
        .order_by(StartupDB.name)
        .all()
    )
    return [
        Startup(
            name=r.name,
            city=r.city or "Unknown",
            category=r.category,
            website=r.website,
            funding_round=r.funding_round,
        )
        for r in rows
        if r.website
    ]


def _score_text_for_skills(text: str, skills: list[str]) -> int:
    """Simple overlap count for ranking seed companies (case-insensitive)."""
    if not skills:
        return 0
    lower = text.lower()
    return sum(1 for s in skills if s.strip() and s.lower() in lower)


def get_seed_companies(
    db: Session,
    limit: int = 10,
    skills: list[str] | None = None,
    role_keywords: list[str] | None = None,
) -> list[str]:
    """Company names from BigSet imports, ranked by overlap with user skills/roles."""
    from app.models.db_models import JobPostingDB

    keywords = [k for k in (skills or []) + (role_keywords or []) if k and k.strip()]
    startups = db.query(StartupDB).filter(StartupDB.category == BIGSET_CATEGORY).all()
    if not keywords:
        return sorted(s.name for s in startups if s.name)[:limit]

    scored: list[tuple[int, str]] = []
    for s in startups:
        if not s.name:
            continue
        blob = " ".join(
            filter(
                None,
                [s.name, s.city or "", s.funding_round or "", s.website or ""],
            )
        )
        jobs = db.query(JobPostingDB).filter(JobPostingDB.company == s.name).limit(5).all()
        for j in jobs:
            blob += f" {j.title or ''} {j.raw_text or ''}"
        scored.append((_score_text_for_skills(blob, keywords), s.name))

    scored.sort(key=lambda x: (-x[0], x[1]))
    matched = [name for score, name in scored if score > 0]
    if matched:
        return matched[:limit]
    return [name for _, name in scored][:limit]


def should_skip_scrape(db: Session, startup_name: str) -> bool:
    """Skip career scrape if recently scanned and within skip window."""
    hours = getattr(settings, "BIGSET_SKIP_SCRAPE_HOURS", 0)
    if hours <= 0:
        return False
    row = db.query(StartupDB).filter(StartupDB.name == startup_name).first()
    if not row or not row.last_scanned:
        return False
    scanned = row.last_scanned
    if scanned.tzinfo:
        scanned = scanned.replace(tzinfo=None)
    now = _utc_now().replace(tzinfo=None)
    age_h = (now - scanned).total_seconds() / 3600
    return age_h < hours


def mark_startup_scanned(
    db: Session,
    startup_name: str,
    *,
    website: str | None = None,
    city: str | None = None,
) -> None:
    """Record last career-page scan time; upsert StartupDB if missing."""
    row = db.query(StartupDB).filter(StartupDB.name == startup_name).first()
    now = _utc_now()
    if row:
        row.last_scanned = now
        if website:
            row.website = website
        if city:
            row.city = city
    else:
        db.add(
            StartupDB(
                name=startup_name,
                city=city or "Unknown",
                category="Scanner",
                website=website,
                last_scanned=now,
            )
        )
    db.commit()


_import_state_path = Path(".bigset_import_state.json")


def _load_folder_state() -> dict[str, float]:
    import json

    if not _import_state_path.exists():
        return {}
    try:
        raw = json.loads(_import_state_path.read_text(encoding="utf-8"))
        return raw if isinstance(raw, dict) else {}
    except Exception:
        return {}


def _save_folder_state(state: dict[str, float]) -> None:
    import json

    _import_state_path.write_text(json.dumps(state), encoding="utf-8")


async def import_changed_files_in_dir(
    directory: Path | None = None,
    mapping_id: str | None = None,
) -> list[BigSetImportResult]:
    """Idempotent folder watch: import CSV/XLSX whose mtime changed since last run."""
    directory = directory or Path(getattr(settings, "BIGSET_IMPORT_DIR", "data/bigset_imports"))

    with _acquire_folder_import_lock(directory) as acquired:
        if not acquired:
            logger.info("BigSet folder import skipped — lock held by another process")
            return []

        state = _load_folder_state()
        results: list[BigSetImportResult] = []

        from app.services.db_service import get_db_session

        for path in sorted(directory.glob("*")):
            if path.suffix.lower() not in {".csv", ".xlsx", ".xlsm"}:
                continue
            mtime = path.stat().st_mtime
            if state.get(str(path)) == mtime:
                continue
            db = get_db_session()
            try:
                svc = BigSetImportService(db)
                content = path.read_bytes()
                result = await svc.import_file(content, path.name, mapping_id)
                results.append(result)
                if result.success:
                    state[str(path)] = mtime
            finally:
                db.close()

        _save_folder_state(state)
        return results
