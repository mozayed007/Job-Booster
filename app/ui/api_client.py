"""Async HTTP client for the Job_Booster API.

Every async function in this module calls one backend API endpoint.
Sync Gradio wrappers live in frontend.py and call these via _run_async().
"""

import os
import tempfile
from pathlib import Path
from typing import Any, cast

import httpx
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")


def _auth_headers(token: str | None) -> dict[str, str]:
    if token and token.strip():
        return {"Authorization": f"Bearer {token.strip()}"}
    return {}


def _handle_json_response(resp: httpx.Response) -> dict:
    """Raise on transport/HTTP errors and return parsed JSON, or an error dict."""
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        text = e.response.text or "Unknown error"
        logger.error(f"HTTP {status} from API: {text[:200]}")
        return {"Error": f"HTTP {status}: {text[:200]}"}
    except httpx.RequestError as e:
        logger.error(f"API request failed: {e}")
        return {"Error": f"Request error: {e}"}

    try:
        return cast(dict[Any, Any], resp.json())
    except Exception as e:
        logger.error(f"Invalid JSON from API (HTTP {resp.status_code}): {e}")
        return {"Error": f"Invalid JSON response (HTTP {resp.status_code})"}


def _success_data(data: dict) -> dict:
    if data.get("success"):
        payload = data.get("data", data)
        return cast(dict[Any, Any], payload)
    return {"Error": data.get("message", data.get("detail", "Unknown error"))}


def _save_response_to_temp(resp: httpx.Response, suffix: str, prefix: str) -> str | None:
    """Write a binary response to a temporary file. Cleans up on failure."""
    try:
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        status = e.response.status_code
        text = e.response.text[:200]
        logger.error(f"Binary download failed (HTTP {status}): {text}")
        return None
    except httpx.RequestError as e:
        logger.error(f"Binary download request failed: {e}")
        return None

    tmp_path: str | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix, prefix=prefix) as tmp:
            tmp.write(resp.content)
            tmp_path = tmp.name
        return tmp_path
    except Exception as e:
        logger.error(f"Failed to write temp file: {e}")
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
        return None


# ---------------------------------------------------------------------------
# Parse endpoints
# ---------------------------------------------------------------------------


async def parse_resume(resume_file: str) -> dict:
    """Upload file to POST /api/parse/resume."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            resp = await client.post(f"{API_URL}/api/parse/resume", files=files)
        return _success_data(_handle_json_response(resp))


async def parse_job(job_description: str) -> dict:
    """Send text to POST /api/parse/job."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/parse/job",
            json={"text": job_description},
        )
        return _success_data(_handle_json_response(resp))


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
        result = _success_data(_handle_json_response(resp))
        if isinstance(result, dict) and "Error" in result:
            return result, {}, {}
        return result, {}, {}


# ---------------------------------------------------------------------------
# Tailor / export endpoints
# ---------------------------------------------------------------------------


async def tailor_resume(
    resume_file: str, job_description: str, format_type: str
) -> tuple[str, list[Any], dict, dict]:
    """Upload resume + job + format to POST /api/tailor."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {"job_text": job_description, "format_type": format_type}
            resp = await client.post(f"{API_URL}/api/tailor", files=files, data=data)
        result = _handle_json_response(resp)
        if result.get("success"):
            d = result["data"]
            return d["tailored_content"], d.get("improvements", []), {}, {}
        return result.get("message", "Error"), [], {}, {}


async def export_content(content: str, format_type: str, title: str) -> str | None:
    """Send content to POST /api/export and save to temp file. Returns file path."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        data = {"content": content, "format_type": format_type, "title": title}
        resp = await client.post(f"{API_URL}/api/export", data=data)
    ext_map = {
        "text/plain": "txt",
        "text/html": "html",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
        "application/pdf": "pdf",
    }
    ext = ext_map.get(resp.headers.get("content-type", ""), "txt")
    return _save_response_to_temp(resp, suffix=f".{ext}", prefix="job_export_")


async def tailor_to_template(resume_file: str, job_description: str) -> str | None:
    """Upload to POST /api/tailor-to-template and save to temp file."""
    async with httpx.AsyncClient(timeout=180.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            data = {"job_text": job_description}
            resp = await client.post(f"{API_URL}/api/tailor-to-template", files=files, data=data)
    return _save_response_to_temp(resp, suffix=".tex", prefix="resume_")


# ---------------------------------------------------------------------------
# Cover letter
# ---------------------------------------------------------------------------


async def cover_letter(
    resume_file: str, job_description: str, company_name: str, hiring_manager: str
) -> tuple[str, list[Any]]:
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
        result = _handle_json_response(resp)
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
        return _success_data(_handle_json_response(resp))


# ---------------------------------------------------------------------------
# Recommendations
# ---------------------------------------------------------------------------


async def recommend_jobs(resume_id: int) -> dict:
    """GET /api/recommendations/jobs/{resume_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/jobs/{resume_id}")
        return _success_data(_handle_json_response(resp))


async def recommend_resumes(job_id: int) -> dict:
    """GET /api/recommendations/resumes/{job_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/resumes/{job_id}")
        return _success_data(_handle_json_response(resp))


async def skill_gap(resume_id: int, job_id: int) -> dict:
    """GET /api/recommendations/skill-gap/{resume_id}/{job_id}."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/skill-gap/{resume_id}/{job_id}")
        return _success_data(_handle_json_response(resp))


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
        return _success_data(_handle_json_response(resp))


async def list_applications() -> dict:
    """GET /api/applications."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications")
        return _success_data(_handle_json_response(resp))


async def application_stats() -> dict:
    """GET /api/applications/stats."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications/stats")
        return _success_data(_handle_json_response(resp))


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


async def analytics_dashboard() -> dict:
    """GET /api/analytics/dashboard."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/dashboard")
        return _success_data(_handle_json_response(resp))


async def skill_trends() -> dict:
    """GET /api/analytics/skills."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/skills")
        return _success_data(_handle_json_response(resp))


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
        return _success_data(_handle_json_response(resp))


async def auth_login(email: str, password: str) -> dict:
    """POST /api/auth/login."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/login",
            json={"email": email, "password": password},
        )
        return _success_data(_handle_json_response(resp))


async def auth_me(token: str) -> dict:
    """GET /api/auth/me."""
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{API_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        return _success_data(_handle_json_response(resp))


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
        return _success_data(_handle_json_response(resp))


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


async def pipeline_list() -> dict:
    """GET /api/pipeline/list."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/pipeline/list")
        return _handle_json_response(resp)


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
        return _handle_json_response(resp)


async def pipeline_run_status(token: str, job_id: str) -> dict:
    """GET /api/pipeline/run/{job_id}."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/pipeline/run/{job_id}",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return _handle_json_response(resp)


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
        return _success_data(_handle_json_response(resp))


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
        return _handle_json_response(resp)


async def discovery_index(jobs: list) -> dict:
    """POST /api/discovery/index."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/index",
            json={"jobs": jobs},
        )
        return _handle_json_response(resp)


async def discovery_sources() -> dict:
    """GET /api/discovery/sources."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/discovery/sources")
        return _handle_json_response(resp)


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
            return {"Error": "Login required - use Account tab to get a token"}
        return _handle_json_response(resp)


async def discovery_bigset_sync(token: str) -> dict:
    """POST /api/discovery/bigset/sync (requires auth)."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{API_URL}/api/discovery/bigset/sync",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return _handle_json_response(resp)


async def discovery_bigset_mappings() -> dict:
    """GET /api/discovery/bigset/mappings."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/discovery/bigset/mappings")
        return _handle_json_response(resp)


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
        return _handle_json_response(resp)


async def discovery_bigset_remote_status(token: str) -> dict:
    """GET /api/discovery/bigset/remote/status."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(
            f"{API_URL}/api/discovery/bigset/remote/status",
            headers=_auth_headers(token),
        )
        if resp.status_code == 401:
            return {"Error": "Login required"}
        return _handle_json_response(resp)


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
        return _handle_json_response(resp)


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
        return _handle_json_response(resp)


# ---------------------------------------------------------------------------
# Scanner
# ---------------------------------------------------------------------------


async def scanner_progress() -> dict:
    """GET /api/scanner/progress."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/scanner/progress")
        return _handle_json_response(resp)


async def scanner_scan_batch(batch_size: int) -> dict:
    """POST /api/scanner/scan/batch."""
    async with httpx.AsyncClient(timeout=300.0) as client:
        resp = await client.post(
            f"{API_URL}/api/scanner/scan/batch",
            params={"batch_size": int(batch_size)},
        )
        return _handle_json_response(resp)


async def scanner_reset() -> dict:
    """POST /api/scanner/reset."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.post(f"{API_URL}/api/scanner/reset")
        return _handle_json_response(resp)


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
        data = _handle_json_response(resp)
        if isinstance(data, list):
            return cast(list[Any], data)
        return cast(list[Any], data.get("jobs", []))


async def scanner_cities() -> dict:
    """GET /api/scanner/cities."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(f"{API_URL}/api/scanner/cities")
        return _handle_json_response(resp)


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
        return _success_data(_handle_json_response(resp))


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
        return _success_data(_handle_json_response(resp))


async def health_check() -> dict:
    """GET /health or root - lightweight API reachability."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        for path in ("/health", "/api/health", "/"):
            try:
                resp = await client.get(f"{API_URL}{path}")
                if resp.status_code < 500:
                    return {"ok": True, "status": resp.status_code, "path": path}
            except Exception:
                continue
        return {"ok": False, "Error": f"Cannot reach API at {API_URL}"}
