"""Async HTTP client for the Job_Booster API.

Every async function in this module calls one backend API endpoint.
Sync Gradio wrappers live in frontend.py and call these via _run_async().
"""

import os
import tempfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")


def _auth_headers(token: str | None) -> dict[str, str]:
    if token and token.strip():
        return {"Authorization": f"Bearer {token.strip()}"}
    return {}


def _unwrap(data: dict) -> dict:
    if data.get("success"):
        return data.get("data", data)
    return {"Error": data.get("message", data.get("detail", "Unknown error"))}


# ---------------------------------------------------------------------------
# Parse endpoints
# ---------------------------------------------------------------------------


async def parse_resume(resume_file: str) -> dict:
    """Upload file to POST /api/parse/resume."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            resp = await client.post(f"{API_URL}/api/parse/resume", files=files)
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def parse_job(job_description: str) -> dict:
    """Send text to POST /api/parse/job."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/parse/job",
            json={"text": job_description},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Analyze endpoints
# ---------------------------------------------------------------------------


async def analyze(resume_file: str, job_description: str) -> tuple[dict, dict, dict]:
    """Upload resume + job text to POST /api/analyze."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {"job_text": job_description}
            resp = await client.post(f"{API_URL}/api/analyze", files=files, data=data)
        result = resp.json()
        if result.get("success"):
            return result["data"], {}, {}
        return {"Error": result.get("message", "Unknown error")}, {}, {}


# ---------------------------------------------------------------------------
# Tailor / export endpoints
# ---------------------------------------------------------------------------


async def tailor_resume(
    resume_file: str, job_description: str, format_type: str
) -> tuple[str, dict, dict, dict]:
    """Upload resume + job + format to POST /api/tailor."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {"job_text": job_description, "format_type": format_type}
            resp = await client.post(f"{API_URL}/api/tailor", files=files, data=data)
        result = resp.json()
        if result.get("success"):
            d = result["data"]
            return d["tailored_content"], d.get("improvements", [])
        return result.get("message", "Error"), []


async def export_content(content: str, format_type: str, title: str) -> str | None:
    """Send content to POST /api/export and save to temp file. Returns file path."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        data = {"content": content, "format_type": format_type, "title": title}
        resp = await client.post(f"{API_URL}/api/export", data=data)
    if resp.status_code != 200:
        logger.error(f"Export failed: {resp.text}")
        return None
    ext_map = {
        "text/plain": "txt",
        "text/html": "html",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/pdf": "pdf",
    }
    ext = ext_map.get(resp.headers.get("content-type", ""), "txt")
    suffix = f".{ext}"
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix="job_export_")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


async def tailor_to_template(resume_file: str, job_description: str) -> str | None:
    """Upload to POST /api/tailor-to-template and save to temp file."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {"job_text": job_description}
            resp = await client.post(f"{API_URL}/api/tailor-to-template", files=files, data=data)
    if resp.status_code != 200:
        logger.error(f"Template tailor failed: {resp.text}")
        return None
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".tex", prefix="resume_")
    tmp.write(resp.content)
    tmp.close()
    return tmp.name


# ---------------------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------------------


async def cover_letter(
    resume_file: str, job_description: str, company_name: str, hiring_manager: str
) -> tuple[str, dict]:
    """Upload resume + job text to POST /api/cover-letter."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {
                "job_text": job_description,
                "company_name": company_name or "",
                "hiring_manager": hiring_manager or "",
            }
            resp = await client.post(f"{API_URL}/api/cover-letter", files=files, data=data)
        result = resp.json()
        if result.get("success"):
            d = result["data"]
            return d["cover_letter"], d.get("key_highlights", [])
        return result.get("message", "Error"), []


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------


async def search(query: str, collection: str, n_results: int) -> dict:
    """POST /api/search/hybrid."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/search/hybrid",
            json={"query": query, "collection": collection, "n_results": n_results},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


async def recommend_jobs(resume_id: int) -> dict:
    """GET /api/recommendations/jobs/{resume_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/jobs/{resume_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def recommend_resumes(job_id: int) -> dict:
    """GET /api/recommendations/resumes/{job_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/resumes/{job_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def skill_gap(resume_id: int, job_id: int) -> dict:
    """GET /api/recommendations/skill-gap/{resume_id}/{job_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/skill-gap/{resume_id}/{job_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Application tracker
# ---------------------------------------------------------------------------


async def track_application(
    company_name: str, position_title: str, status: str, notes: str
) -> dict:
    """POST /api/applications."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/applications",
            json={
                "company_name": company_name,
                "position_title": position_title,
                "status": status,
                "notes": notes,
            },
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def list_applications() -> dict:
    """GET /api/applications."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def application_stats() -> dict:
    """GET /api/applications/stats."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications/stats")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


async def analytics_dashboard() -> dict:
    """GET /api/analytics/dashboard."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/dashboard")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def skill_trends() -> dict:
    """GET /api/analytics/skills."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/skills")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------


async def auth_register(email: str, password: str, name: str) -> dict:
    """POST /api/auth/register."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/register",
            json={"email": email, "password": password, "name": name},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def auth_login(email: str, password: str) -> dict:
    """POST /api/auth/login."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/login",
            json={"email": email, "password": password},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def auth_me(token: str) -> dict:
    """GET /api/auth/me."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{API_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


async def dashboard(resume_id: int | None = None) -> dict:
    """GET /api/dashboard."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        params = {}
        if resume_id:
            params["resume_id"] = resume_id
        resp = await client.get(f"{API_URL}/api/dashboard", params=params)
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def pipeline_list() -> dict:
    """GET /api/pipeline/list."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/pipeline/list")
        return resp.json()


async def pipeline_run(
    token: str,
    pipeline_key: str,
    *,
    resume_text: str = "",
    job_text: str = "",
    cv_text: str = "",
    inputs: dict | None = None,
    background: bool = False,
) -> dict:
    """POST /api/pipeline/run (requires auth)."""
    async with httpx.AsyncClient(timeout=600.0) as client:
        resp = await client.post(
            f"{API_URL}/api/pipeline/run",
            params={"background": background} if background else None,
            json={
                "pipeline_key": pipeline_key,
                "resume_text": resume_text,
                "job_text": job_text,
                "cv_text": cv_text,
                "inputs": inputs or {},
            },
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def pipeline_run_status(token: str, job_id: str) -> dict:
    """GET /api/pipeline/run/{job_id}."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/pipeline/run/{job_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def pipeline_apply(
    resume_file: str, job_text: str, company_name: str, hiring_manager: str, format_type: str
) -> dict:
    """POST /api/pipeline/apply/file."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {
                "job_text": job_text,
                "company_name": company_name or "",
                "hiring_manager": hiring_manager or "",
                "format_type": format_type,
            }
            resp = await client.post(f"{API_URL}/api/pipeline/apply/file", files=files, data=data)
        result = resp.json()
        if result.get("success"):
            return result["data"]
        return {"Error": result.get("message", "Unknown error")}


# ---------------------------------------------------------------------------
# Job Discovery
# ---------------------------------------------------------------------------


async def discovery_search(query: str, location: str, sources: list) -> dict:
    """POST /api/discovery/search."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/search",
            json={"query": query, "location": location, "sources": sources or None},
        )
        data = resp.json()
        if data.get("success"):
            return data
        return {"Error": data.get("message", "Unknown error")}


async def discovery_index(jobs: list) -> dict:
    """POST /api/discovery/index."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/index",
            json={"jobs": jobs},
        )
        data = resp.json()
        if data.get("success"):
            return data
        return {"Error": data.get("message", "Unknown error")}


async def discovery_sources() -> dict:
    """GET /api/discovery/sources."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/discovery/sources")
        return resp.json()


async def discovery_ranked_jobs(
    token: str,
    *,
    limit: int = 25,
    min_score: float | None = None,
    query: str = "",
) -> dict:
    """GET /api/discovery/jobs/ranked (requires auth)."""
    params: dict = {"limit": limit}
    if min_score is not None:
        params["min_score"] = min_score
    if query.strip():
        params["query"] = query.strip()
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.get(
            f"{API_URL}/api/discovery/jobs/ranked",
            params=params,
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required — use Account tab to get a token"}
        data = resp.json()
        if data.get("success"):
            return data
        return {"Error": data.get("detail", data.get("message", resp.text))}


async def discovery_bigset_sync(token: str) -> dict:
    """POST /api/discovery/bigset/sync (requires auth)."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/bigset/sync",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def discovery_bigset_mappings() -> dict:
    """GET /api/discovery/bigset/mappings."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/discovery/bigset/mappings")
        return resp.json()


async def discovery_bigset_preview(
    token: str,
    file_path: str,
    mapping_id: str | None = None,
) -> dict:
    """POST /api/discovery/bigset/preview (requires auth)."""
    path = Path(file_path)
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": (path.name, f)}
            data = {}
            if mapping_id and mapping_id.strip():
                data["mapping_id"] = mapping_id.strip()
            resp = await client.post(
                f"{API_URL}/api/discovery/bigset/preview",
                files=files,
                data=data,
                headers=_auth_headers(token),
            )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        try:
            return resp.json()
        except Exception:
            return {"Error": resp.text or f"HTTP {resp.status_code}"}


async def discovery_bigset_remote_status(token: str) -> dict:
    """GET /api/discovery/bigset/remote/status."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/discovery/bigset/remote/status",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def discovery_bigset_remote_trigger(token: str, force: bool = False) -> dict:
    """POST /api/discovery/bigset/remote/trigger."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/bigset/remote/trigger",
            json={"force": force},
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def discovery_bigset_import(
    token: str,
    file_path: str,
    mapping_id: str | None = None,
) -> dict:
    """POST /api/discovery/bigset/import (requires auth)."""
    path = Path(file_path)
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(file_path, "rb") as f:
            files = {"file": (path.name, f)}
            data = {}
            if mapping_id and mapping_id.strip():
                data["mapping_id"] = mapping_id.strip()
            resp = await client.post(
                f"{API_URL}/api/discovery/bigset/import",
                files=files,
                data=data,
                headers=_auth_headers(token),
            )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        try:
            return resp.json()
        except Exception:
            return {"Error": resp.text or f"HTTP {resp.status_code}"}


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


async def scanner_progress() -> dict:
    """GET /api/scanner/progress."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/scanner/progress")
        return resp.json()


async def scanner_scan_batch(batch_size: int) -> dict:
    """POST /api/scanner/scan/batch."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{API_URL}/api/scanner/scan/batch",
            params={"batch_size": int(batch_size)},
        )
        return resp.json()


async def scanner_reset() -> dict:
    """POST /api/scanner/reset."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{API_URL}/api/scanner/reset")
        return resp.json()


async def scanner_top_jobs(limit: int = 50, city: str | None = None) -> list:
    """GET /api/scanner/jobs/top."""
    params: dict = {"limit": limit}
    if city and city.strip().lower() != "all":
        params["city"] = city.strip()
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/scanner/jobs/top",
            params=params,
        )
        data = resp.json()
        if isinstance(data, list):
            return data
        return data.get("jobs", [])


async def scanner_cities() -> dict:
    """GET /api/scanner/cities."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/scanner/cities")
        return resp.json()


# ---------------------------------------------------------------------------
# Settings profile
# ---------------------------------------------------------------------------


async def settings_get_profile(token: str) -> dict:
    """GET /api/settings/profile."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/settings/profile",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return resp.json()


async def settings_put_profile(token: str, profile: dict) -> dict:
    """PUT /api/settings/profile."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.put(
            f"{API_URL}/api/settings/profile",
            json=profile,
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        try:
            return resp.json()
        except Exception:
            return {"Error": resp.text or f"HTTP {resp.status_code}"}


async def health_check() -> dict:
    """GET /health or root — lightweight API reachability."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        for path in ("/health", "/api/health", "/"):
            try:
                resp = await client.get(f"{API_URL}{path}")
                if resp.status_code < 500:
                    return {"ok": True, "status": resp.status_code, "path": path}
            except Exception:
                continue
        return {"ok": False, "Error": f"Cannot reach API at {API_URL}"}
