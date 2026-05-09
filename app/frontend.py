"""Gradio UI for Job_Booster application."""

import asyncio
import os
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

import gradio as gr
import httpx
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

API_URL = os.getenv("API_URL", "http://localhost:8000")
SUPPORTED_FORMATS = [".pdf", ".docx", ".md", ".txt", ".tex"]

logger.info(f"Initializing Job_Booster UI (API: {API_URL})")


def _run_async(coro):
    """Run an async function from sync Gradio callback."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import nest_asyncio

            nest_asyncio.apply()
            return loop.run_until_complete(coro)
    except RuntimeError:
        pass
    return asyncio.run(coro)


async def _parse_resume_async(resume_file: str) -> Dict:
    """Upload file to POST /api/parse/resume."""
    async with httpx.AsyncClient(timeout=120.0) as client:
        with open(resume_file, "rb") as f:
            files = {"file": (Path(resume_file).name, f)}
            resp = await client.post(f"{API_URL}/api/parse/resume", files=files)
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _parse_job_async(job_description: str) -> Dict:
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


async def _analyze_async(resume_file: str, job_description: str) -> Tuple[Dict, Dict, Dict]:
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


async def _tailor_async(
    resume_file: str, job_description: str, format_type: str
) -> Tuple[str, Dict, Dict, Dict]:
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


async def _export_async(content: str, format_type: str, title: str) -> Optional[str]:
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


async def _template_tailor_async(resume_file: str, job_description: str) -> Optional[str]:
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


def generate_from_template(resume_file: str, job_description: str):
    if not resume_file or not job_description.strip():
        return gr.update(visible=False)
    try:
        result = _run_async(_template_tailor_async(resume_file, job_description))
        if result:
            return gr.update(value=result, visible=True)
        return gr.update(visible=False)
    except Exception as e:
        logger.error(f"template tailor error: {e}")
        return gr.update(visible=False)


def export_tailored_content(content: str, format_type: str, title: str):
    """Sync wrapper for export."""
    if not content or not content.strip():
        return gr.update(visible=False)
    try:
        result = _run_async(_export_async(content, format_type, title))
        if result:
            return gr.update(value=result, visible=True)
        return gr.update(visible=False)
    except Exception as e:
        logger.error(f"export error: {e}")
        return gr.update(visible=False)


def parse_resume(resume_file: str) -> Dict:
    """Sync wrapper for resume parsing."""
    if not resume_file:
        return {"Error": "No file uploaded"}
    try:
        return _run_async(_parse_resume_async(resume_file))
    except Exception as e:
        logger.error(f"parse_resume error: {e}")
        return {"Error": str(e)}


def parse_job(job_description: str) -> Dict:
    """Sync wrapper for job parsing."""
    if not job_description or not job_description.strip():
        return {"Error": "No job description provided"}
    try:
        return _run_async(_parse_job_async(job_description))
    except Exception as e:
        logger.error(f"parse_job error: {e}")
        return {"Error": str(e)}


def analyze_resume_job_match(resume_file: str, job_description: str) -> Tuple[Dict, Dict, Dict]:
    """Sync wrapper for analysis."""
    if not resume_file:
        return {"Error": "No file uploaded"}, {}, {}
    if not job_description or not job_description.strip():
        return {"Error": "No job description provided"}, {}, {}
    try:
        return _run_async(_analyze_async(resume_file, job_description))
    except Exception as e:
        logger.error(f"analyze error: {e}")
        return {"Error": str(e)}, {}, {}


def generate_tailored_resume(
    resume_file: str, job_description: str, format_type: str
) -> Tuple[str, Dict, Dict, Dict]:
    """Sync wrapper for tailoring."""
    if not resume_file:
        return "No file uploaded", {}, {}, {}
    if not job_description or not job_description.strip():
        return "No job description provided", {}, {}, {}
    try:
        return _run_async(_tailor_async(resume_file, job_description, format_type))
    except Exception as e:
        logger.error(f"tailor error: {e}")
        return str(e), {}, {}, {}


async def _cover_letter_async(
    resume_file: str, job_description: str, company_name: str, hiring_manager: str
) -> Tuple[str, Dict]:
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


def generate_cover_letter_ui(
    resume_file: str, job_description: str, company_name: str, hiring_manager: str
) -> Tuple[str, Dict]:
    """Sync wrapper for cover letter generation."""
    if not resume_file:
        return "No file uploaded", {}
    if not job_description or not job_description.strip():
        return "No job description provided", {}
    try:
        return _run_async(
            _cover_letter_async(resume_file, job_description, company_name, hiring_manager)
        )
    except Exception as e:
        logger.error(f"cover letter error: {e}")
        return str(e), {}


# --- Search ---
async def _search_async(query: str, collection: str, n_results: int) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/search/hybrid",
            json={"query": query, "collection": collection, "n_results": n_results},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


def search_ui(query: str, collection: str, n_results: int) -> Dict:
    if not query or not query.strip():
        return {"Error": "No search query provided"}
    try:
        return _run_async(_search_async(query, collection, int(n_results)))
    except Exception as e:
        logger.error(f"search error: {e}")
        return {"Error": str(e)}


# --- Recommendations ---
async def _recommend_jobs_async(resume_id: int) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/jobs/{resume_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _recommend_resumes_async(job_id: int) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/resumes/{job_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _skill_gap_async(resume_id: int, job_id: int) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/recommendations/skill-gap/{resume_id}/{job_id}")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


def recommend_jobs_ui(resume_id: int) -> Dict:
    try:
        return _run_async(_recommend_jobs_async(int(resume_id)))
    except Exception as e:
        logger.error(f"recommend_jobs error: {e}")
        return {"Error": str(e)}


def recommend_resumes_ui(job_id: int) -> Dict:
    try:
        return _run_async(_recommend_resumes_async(int(job_id)))
    except Exception as e:
        logger.error(f"recommend_resumes error: {e}")
        return {"Error": str(e)}


def skill_gap_ui(resume_id: int, job_id: int) -> Dict:
    try:
        return _run_async(_skill_gap_async(int(resume_id), int(job_id)))
    except Exception as e:
        logger.error(f"skill_gap error: {e}")
        return {"Error": str(e)}


# --- Application Tracker ---
async def _track_application_async(
    company_name: str, position_title: str, status: str, notes: str
) -> Dict:
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


async def _list_applications_async() -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _application_stats_async() -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/applications/stats")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


def track_application_ui(
    company_name: str, position_title: str, status: str, notes: str
) -> Dict:
    if not company_name or not company_name.strip():
        return {"Error": "No company name provided"}
    if not position_title or not position_title.strip():
        return {"Error": "No position title provided"}
    try:
        return _run_async(
            _track_application_async(company_name, position_title, status, notes)
        )
    except Exception as e:
        logger.error(f"track_application error: {e}")
        return {"Error": str(e)}


def list_applications_ui():
    try:
        result = _run_async(_list_applications_async())
        if isinstance(result, list):
            return result
        return [result]
    except Exception as e:
        logger.error(f"list_applications error: {e}")
        return [{"Error": str(e)}]


def application_stats_ui() -> Dict:
    try:
        return _run_async(_application_stats_async())
    except Exception as e:
        logger.error(f"application_stats error: {e}")
        return {"Error": str(e)}


# --- Analytics ---
async def _analytics_dashboard_async() -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/dashboard")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _skill_trends_async() -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(f"{API_URL}/api/analytics/skills")
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


def analytics_dashboard_ui() -> Dict:
    try:
        return _run_async(_analytics_dashboard_async())
    except Exception as e:
        logger.error(f"analytics_dashboard error: {e}")
        return {"Error": str(e)}


def skill_trends_ui() -> Dict:
    try:
        return _run_async(_skill_trends_async())
    except Exception as e:
        logger.error(f"skill_trends error: {e}")
        return {"Error": str(e)}


# --- Auth ---
async def _auth_register_async(email: str, password: str, name: str) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/register",
            json={"email": email, "password": password, "name": name},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _auth_login_async(email: str, password: str) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(
            f"{API_URL}/api/auth/login",
            json={"email": email, "password": password},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


async def _auth_me_async(token: str) -> Dict:
    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.get(
            f"{API_URL}/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        data = resp.json()
        if data.get("success"):
            return data["data"]
        return {"Error": data.get("message", "Unknown error")}


def auth_register_ui(email: str, password: str, name: str) -> Tuple[Dict, str]:
    if not email or not email.strip():
        return {"Error": "No email provided"}, ""
    if not password or not password.strip():
        return {"Error": "No password provided"}, ""
    try:
        result = _run_async(_auth_register_async(email, password, name))
        token = result.get("token", "") if isinstance(result, dict) else ""
        return result, f"**Token:** `{token}`" if token else ""
    except Exception as e:
        logger.error(f"auth_register error: {e}")
        return {"Error": str(e)}, ""


def auth_login_ui(email: str, password: str) -> Tuple[Dict, str]:
    if not email or not email.strip():
        return {"Error": "No email provided"}, ""
    if not password or not password.strip():
        return {"Error": "No password provided"}, ""
    try:
        result = _run_async(_auth_login_async(email, password))
        token = result.get("token", "") if isinstance(result, dict) else ""
        return result, f"**Token:** `{token}`" if token else ""
    except Exception as e:
        logger.error(f"auth_login error: {e}")
        return {"Error": str(e)}, ""


def auth_me_ui(token: str) -> Dict:
    if not token or not token.strip():
        return {"Error": "No token provided"}
    try:
        return _run_async(_auth_me_async(token.strip()))
    except Exception as e:
        logger.error(f"auth_me error: {e}")
        return {"Error": str(e)}


# --- Gradio UI ---
with gr.Blocks(title="Job_Booster - Resume Tailoring Assistant") as app:
    gr.Markdown(
        """
        # Job_Booster
        ### AI-Powered Resume Tailoring Assistant

        Upload your resume and a job description to get a tailored resume optimized for the specific job.
        """
    )

    with gr.Tabs():
        # Tab 1: Resume Parser
        with gr.TabItem("Parse Resume"):
            with gr.Row():
                with gr.Column():
                    resume_input = gr.File(
                        label="Upload Resume (PDF, DOCX, MD, TXT, TEX)",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    parse_resume_button = gr.Button("Parse Resume")

                with gr.Column():
                    resume_output = gr.JSON(label="Parsed Resume Data")

            parse_resume_button.click(
                fn=parse_resume,
                inputs=[resume_input],
                outputs=[resume_output],
            )

        # Tab 2: Job Description Parser
        with gr.TabItem("Parse Job Description"):
            with gr.Row():
                with gr.Column():
                    job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10,
                    )
                    parse_job_button = gr.Button("Parse Job Description")

                with gr.Column():
                    job_output = gr.JSON(label="Parsed Job Data")

            parse_job_button.click(
                fn=parse_job,
                inputs=[job_input],
                outputs=[job_output],
            )

        # Tab 3: Resume-Job Analysis
        with gr.TabItem("Analyze Match"):
            with gr.Row():
                with gr.Column():
                    analysis_resume_input = gr.File(
                        label="Upload Resume",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    analysis_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10,
                    )
                    analyze_button = gr.Button("Analyze Match")

                with gr.Column():
                    match_output = gr.JSON(label="Match Analysis")
                    analysis_resume_output = gr.JSON(label="Resume Data")
                    analysis_job_output = gr.JSON(label="Job Data")

            analyze_button.click(
                fn=analyze_resume_job_match,
                inputs=[analysis_resume_input, analysis_job_input],
                outputs=[match_output, analysis_resume_output, analysis_job_output],
            )

        # Tab 4: Tailor Resume
        with gr.TabItem("Tailor Resume"):
            with gr.Row():
                with gr.Column():
                    tailor_resume_input = gr.File(
                        label="Upload Resume",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    tailor_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10,
                    )
                    format_input = gr.Radio(
                        label="Output Format",
                        choices=["text", "html", "docx", "pdf", "latex"],
                        value="text",
                    )
                    tailor_button = gr.Button("Generate Tailored Resume")
                    template_btn = gr.Button("Generate from Template (.tex)", variant="secondary")

                with gr.Column():
                    tailor_output = gr.Textbox(label="Tailored Resume", lines=20)
                    tailor_improvements = gr.JSON(label="Improvements")
                    with gr.Row():
                        export_format = gr.Radio(
                            label="Export Format",
                            choices=["text", "html", "docx", "pdf", "latex"],
                            value="text",
                        )
                        export_btn = gr.Button("Export", variant="secondary")
                    export_download = gr.File(label="Download", visible=False)
                    template_download = gr.File(label="Download Template Resume", visible=False)

            tailor_button.click(
                fn=generate_tailored_resume,
                inputs=[tailor_resume_input, tailor_job_input, format_input],
                outputs=[tailor_output, tailor_improvements],
            )

            export_btn.click(
                fn=export_tailored_content,
                inputs=[tailor_output, export_format, gr.State("Resume")],
                outputs=[export_download],
            )

            template_btn.click(
                fn=generate_from_template,
                inputs=[tailor_resume_input, tailor_job_input],
                outputs=[template_download],
            )

        # Tab 5: Startup Scanner
        with gr.TabItem("Startup Scanner"):
            from app.ui.scanner_tab import create_scanner_tab

            create_scanner_tab()

        # Tab 6: Cover Letter
        with gr.TabItem("Cover Letter"):
            with gr.Row():
                with gr.Column():
                    cl_resume_input = gr.File(
                        label="Upload Resume",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    cl_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10,
                    )
                    cl_company_input = gr.Textbox(
                        label="Company Name (optional)",
                        placeholder="e.g., Google",
                    )
                    cl_manager_input = gr.Textbox(
                        label="Hiring Manager (optional)",
                        placeholder="e.g., John Smith",
                    )
                    cl_button = gr.Button("Generate Cover Letter")
                with gr.Column():
                    cl_output = gr.Textbox(label="Cover Letter", lines=20)
                    cl_highlights = gr.JSON(label="Key Highlights")

            cl_button.click(
                fn=generate_cover_letter_ui,
                inputs=[cl_resume_input, cl_job_input, cl_company_input, cl_manager_input],
                outputs=[cl_output, cl_highlights],
            )

        # Tab 7: Search
        with gr.TabItem("Search"):
            with gr.Row():
                with gr.Column():
                    search_query_input = gr.Textbox(
                        label="Search Query",
                        placeholder="e.g., Python developer with machine learning experience",
                    )
                    search_collection_input = gr.Radio(
                        label="Collection",
                        choices=["resumes", "jobs"],
                        value="resumes",
                    )
                    search_n_results_input = gr.Slider(
                        label="Number of Results",
                        minimum=1,
                        maximum=20,
                        value=5,
                        step=1,
                    )
                    search_button = gr.Button("Search")
                with gr.Column():
                    search_output = gr.JSON(label="Search Results")

            search_button.click(
                fn=search_ui,
                inputs=[search_query_input, search_collection_input, search_n_results_input],
                outputs=[search_output],
            )

        # Tab 8: Recommendations
        with gr.TabItem("Recommendations"):
            with gr.Row():
                with gr.Column():
                    rec_resume_id_input = gr.Number(label="Resume ID", precision=0)
                    rec_jobs_button = gr.Button("Recommend Jobs")
                    rec_jobs_output = gr.JSON(label="Recommended Jobs")

                with gr.Column():
                    rec_job_id_input = gr.Number(label="Job ID", precision=0)
                    rec_resumes_button = gr.Button("Recommend Resumes")
                    rec_resumes_output = gr.JSON(label="Recommended Resumes")

            with gr.Row():
                with gr.Column():
                    sg_resume_id_input = gr.Number(label="Resume ID (Skill Gap)", precision=0)
                    sg_job_id_input = gr.Number(label="Job ID (Skill Gap)", precision=0)
                    skill_gap_button = gr.Button("Skill Gap Analysis")
                with gr.Column():
                    skill_gap_output = gr.JSON(label="Skill Gap Results")

            rec_jobs_button.click(
                fn=recommend_jobs_ui,
                inputs=[rec_resume_id_input],
                outputs=[rec_jobs_output],
            )

            rec_resumes_button.click(
                fn=recommend_resumes_ui,
                inputs=[rec_job_id_input],
                outputs=[rec_resumes_output],
            )

            skill_gap_button.click(
                fn=skill_gap_ui,
                inputs=[sg_resume_id_input, sg_job_id_input],
                outputs=[skill_gap_output],
            )

        # Tab 9: Application Tracker
        with gr.TabItem("Application Tracker"):
            with gr.Row():
                with gr.Column():
                    app_company_input = gr.Textbox(
                        label="Company Name",
                        placeholder="e.g., Google",
                    )
                    app_position_input = gr.Textbox(
                        label="Position Title",
                        placeholder="e.g., Senior Software Engineer",
                    )
                    app_status_input = gr.Dropdown(
                        label="Status",
                        choices=["applied", "interview", "offer", "rejected", "withdrawn"],
                        value="applied",
                    )
                    app_notes_input = gr.Textbox(
                        label="Notes",
                        placeholder="Any additional notes...",
                        lines=3,
                    )
                    track_app_button = gr.Button("Track Application")
                with gr.Column():
                    track_app_output = gr.JSON(label="Tracked Application")

            with gr.Row():
                view_apps_button = gr.Button("View Applications")
                apps_stats_button = gr.Button("Stats")

            apps_dataframe = gr.Dataframe(
                label="Applications",
                headers=["company_name", "position_title", "status", "notes"],
                interactive=False,
            )
            apps_stats_output = gr.JSON(label="Application Stats")

            track_app_button.click(
                fn=track_application_ui,
                inputs=[app_company_input, app_position_input, app_status_input, app_notes_input],
                outputs=[track_app_output],
            )

            view_apps_button.click(
                fn=list_applications_ui,
                inputs=[],
                outputs=[apps_dataframe],
            )

            apps_stats_button.click(
                fn=application_stats_ui,
                inputs=[],
                outputs=[apps_stats_output],
            )

        # Tab 10: Analytics
        with gr.TabItem("Analytics"):
            with gr.Row():
                with gr.Column():
                    dashboard_button = gr.Button("Load Dashboard")
                with gr.Column():
                    dashboard_output = gr.JSON(label="Dashboard")

            with gr.Row():
                with gr.Column():
                    skills_button = gr.Button("Skill Trends")
                with gr.Column():
                    skills_output = gr.JSON(label="Skill Trends")

            dashboard_button.click(
                fn=analytics_dashboard_ui,
                inputs=[],
                outputs=[dashboard_output],
            )

            skills_button.click(
                fn=skill_trends_ui,
                inputs=[],
                outputs=[skills_output],
            )

        # Tab 11: Auth
        with gr.TabItem("Auth"):
            with gr.Row():
                with gr.Column():
                    auth_email_input = gr.Textbox(
                        label="Email",
                        placeholder="you@example.com",
                    )
                    auth_password_input = gr.Textbox(
                        label="Password",
                        type="password",
                    )
                    auth_name_input = gr.Textbox(
                        label="Name",
                        placeholder="Your Name",
                    )
                    with gr.Row():
                        register_button = gr.Button("Register")
                        login_button = gr.Button("Login")
                with gr.Column():
                    auth_token_display = gr.Markdown(label="Token")
                    auth_result_output = gr.JSON(label="Auth Result")

            with gr.Row():
                with gr.Column():
                    profile_token_input = gr.Textbox(
                        label="Token",
                        placeholder="Paste your JWT token here...",
                    )
                    profile_button = gr.Button("My Profile")
                with gr.Column():
                    profile_output = gr.JSON(label="Profile")

            register_button.click(
                fn=auth_register_ui,
                inputs=[auth_email_input, auth_password_input, auth_name_input],
                outputs=[auth_result_output, auth_token_display],
            )

            login_button.click(
                fn=auth_login_ui,
                inputs=[auth_email_input, auth_password_input],
                outputs=[auth_result_output, auth_token_display],
            )

            profile_button.click(
                fn=auth_me_ui,
                inputs=[profile_token_input],
                outputs=[profile_output],
            )

    gr.Markdown(
        """
        ## How It Works
        1. **Parse Resume**: Upload your resume to extract structured information
        2. **Parse Job Description**: Enter a job description to extract key requirements
        3. **Analyze Match**: Compare your resume against the job description
        4. **Tailor Resume**: Generate an optimized version of your resume for the job
        5. **Startup Scanner**: Scan AI/ML startup career pages for relevant jobs
        6. **Cover Letter**: Generate a personalized cover letter for your job application
        7. **Search**: Semantic search across resumes and jobs
        8. **Recommendations**: Job recommendations and skill gap analysis
        9. **Application Tracker**: Track and manage job applications
        10. **Analytics**: Dashboard with stats and skill trends
        11. **Auth**: Register, login, and manage your profile

        Powered by Pydantic AI + LiteLLM
        """
    )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=8050)
