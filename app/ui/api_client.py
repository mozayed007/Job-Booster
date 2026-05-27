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
