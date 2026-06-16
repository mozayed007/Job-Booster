"""Discovery / BigSet tools for Pydantic AI agents and MCP."""

from __future__ import annotations

import asyncio
import json
from typing import Any

from pydantic_ai import Tool

from app.services.bigset_import_service import (
    import_changed_files_in_dir,
    list_imported_startups,
    list_mapping_ids,
)
from app.services.db_service import get_db_session
from app.services.discovery_query_service import search_imported_jobs
from app.services.job_fit_service import jobs_for_company, rank_imported_jobs
from app.services.user_profile_service import load_user_profile


def _list_startups_sync(limit: int) -> list[dict[str, Any]]:
    """Synchronous database work for list_imported_startups_tool."""
    profile = load_user_profile()
    db = get_db_session()
    try:
        startups = list_imported_startups(db)
        ranked = rank_imported_jobs(db, profile, limit=limit)
        by_company = {r["company"]: r.get("fit_score") for r in ranked if r.get("company")}
        return [
            {
                "name": s.name,
                "website": s.website,
                "city": s.city,
                "fit_hint": by_company.get(s.name),
            }
            for s in startups[:limit]
        ]
    finally:
        db.close()


def _jobs_for_company_sync(company: str, limit: int) -> list[dict[str, Any]]:
    """Synchronous database work for imported_jobs_for_company_tool."""
    db = get_db_session()
    try:
        jobs = jobs_for_company(db, company, limit=min(max(limit, 1), 20))
        return [
            {
                "id": j.id,
                "title": j.title,
                "location": j.location,
                "source_url": j.source_url,
                "snippet": (j.raw_text or "")[:300],
            }
            for j in jobs
        ]
    finally:
        db.close()


async def search_imported_jobs_tool(
    query: str,
    limit: int = 10,
) -> str:
    """Search imported BigSet job postings (semantic + profile fit)."""
    results = await search_imported_jobs(query, limit=min(max(limit, 1), 25))
    return json.dumps(results, indent=2)


async def list_imported_startups_tool(limit: int = 20) -> str:
    """List startups imported from BigSet with websites."""
    payload = await asyncio.to_thread(_list_startups_sync, limit)
    return json.dumps(payload, indent=2)


async def list_bigset_mappings_tool() -> str:
    """List BigSet CSV/XLSX column mapping profiles."""
    return json.dumps(list_mapping_ids(), indent=2)


async def sync_bigset_folder_tool() -> str:
    """Import changed files from BIGSET_IMPORT_DIR (folder watch)."""
    results = await import_changed_files_in_dir()
    summary = [
        {
            "mapping_id": r.mapping_id,
            "stored": r.stored,
            "startups_upserted": r.startups_upserted,
            "skipped_duplicates": r.skipped_duplicates,
            "success": r.success,
            "errors": r.errors,
        }
        for r in results
    ]
    return json.dumps({"files_processed": len(summary), "results": summary}, indent=2)


async def imported_jobs_for_company_tool(company: str, limit: int = 5) -> str:
    """Return imported job stubs/listings for one company."""
    payload = await asyncio.to_thread(_jobs_for_company_sync, company, limit)
    return json.dumps(payload, indent=2)


search_imported_jobs_tool_wrapped = Tool(
    search_imported_jobs_tool,
    takes_ctx=False,
    description="Search imported BigSet jobs by query; returns JSON with fit scores.",
)

list_imported_startups_tool_wrapped = Tool(
    list_imported_startups_tool,
    takes_ctx=False,
    description="List BigSet-imported companies with websites and fit hints.",
)

list_bigset_mappings_tool_wrapped = Tool(
    list_bigset_mappings_tool,
    takes_ctx=False,
    description="List available BigSet CSV column mapping profiles.",
)

sync_bigset_folder_tool_wrapped = Tool(
    sync_bigset_folder_tool,
    takes_ctx=False,
    description="Import new/changed CSV/XLSX files from the BigSet import folder.",
)

imported_jobs_for_company_tool_wrapped = Tool(
    imported_jobs_for_company_tool,
    takes_ctx=False,
    description="Get imported job rows for a single company name.",
)

# Registry names for MCP / ax_tool_registry
TOOL_HANDLERS = {
    "search_imported_jobs": search_imported_jobs_tool,
    "list_imported_startups": list_imported_startups_tool,
    "list_bigset_mappings": list_bigset_mappings_tool,
    "sync_bigset_folder": sync_bigset_folder_tool,
    "imported_jobs_for_company": imported_jobs_for_company_tool,
    "web_search": None,
    "web_fetch": None,
}
