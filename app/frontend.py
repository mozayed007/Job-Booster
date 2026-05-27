"""Gradio UI for Job_Booster application."""

import asyncio

import gradio as gr
from loguru import logger

from app.ui.api_client import (
    analytics_dashboard,
    application_stats,
    auth_login,
    auth_me,
    auth_register,
    dashboard,
    discovery_index,
    discovery_search,
    list_applications,
    pipeline_apply,
    recommend_jobs,
    recommend_resumes,
    search,
    skill_gap,
    skill_trends,
    track_application,
)

logger.info("Initializing Job_Booster UI")


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





def search_ui(query: str, collection: str, n_results: int) -> dict:
    if not query or not query.strip():
        return {"Error": "No search query provided"}
    try:
        return _run_async(search(query, collection, int(n_results)))
    except Exception as e:
        logger.error(f"search error: {e}")
        return {"Error": str(e)}


def recommend_jobs_ui(resume_id: int) -> dict:
    try:
        return _run_async(recommend_jobs(int(resume_id)))
    except Exception as e:
        logger.error(f"recommend_jobs error: {e}")
        return {"Error": str(e)}


def recommend_resumes_ui(job_id: int) -> dict:
    try:
        return _run_async(recommend_resumes(int(job_id)))
    except Exception as e:
        logger.error(f"recommend_resumes error: {e}")
        return {"Error": str(e)}


def skill_gap_ui(resume_id: int, job_id: int) -> dict:
    try:
        return _run_async(skill_gap(int(resume_id), int(job_id)))
    except Exception as e:
        logger.error(f"skill_gap error: {e}")
        return {"Error": str(e)}


def track_application_ui(
    company_name: str, position_title: str, status: str, notes: str
) -> dict:
    if not company_name or not company_name.strip():
        return {"Error": "No company name provided"}
    if not position_title or not position_title.strip():
        return {"Error": "No position title provided"}
    try:
        return _run_async(
            track_application(company_name, position_title, status, notes)
        )
    except Exception as e:
        logger.error(f"track_application error: {e}")
        return {"Error": str(e)}


def list_applications_ui():
    try:
        result = _run_async(list_applications())
        if isinstance(result, list):
            return result
        return [result]
    except Exception as e:
        logger.error(f"list_applications error: {e}")
        return [{"Error": str(e)}]


def application_stats_ui() -> dict:
    try:
        return _run_async(application_stats())
    except Exception as e:
        logger.error(f"application_stats error: {e}")
        return {"Error": str(e)}


def analytics_dashboard_ui() -> dict:
    try:
        return _run_async(analytics_dashboard())
    except Exception as e:
        logger.error(f"analytics_dashboard error: {e}")
        return {"Error": str(e)}


def skill_trends_ui() -> dict:
    try:
        return _run_async(skill_trends())
    except Exception as e:
        logger.error(f"skill_trends error: {e}")
        return {"Error": str(e)}


def auth_register_ui(email: str, password: str, name: str) -> tuple[dict, str]:
    if not email or not email.strip():
        return {"Error": "No email provided"}, ""
    if not password or not password.strip():
        return {"Error": "No password provided"}, ""
    try:
        result = _run_async(auth_register(email, password, name))
        token = result.get("token", "") if isinstance(result, dict) else ""
        return result, f"**Token:** `{token}`" if token else ""
    except Exception as e:
        logger.error(f"auth_register error: {e}")
        return {"Error": str(e)}, ""


def auth_login_ui(email: str, password: str) -> tuple[dict, str]:
    if not email or not email.strip():
        return {"Error": "No email provided"}, ""
    if not password or not password.strip():
        return {"Error": "No password provided"}, ""
    try:
        result = _run_async(auth_login(email, password))
        token = result.get("token", "") if isinstance(result, dict) else ""
        return result, f"**Token:** `{token}`" if token else ""
    except Exception as e:
        logger.error(f"auth_login error: {e}")
        return {"Error": str(e)}, ""


def auth_me_ui(token: str) -> dict:
    if not token or not token.strip():
        return {"Error": "No token provided"}
    try:
        return _run_async(auth_me(token.strip()))
    except Exception as e:
        logger.error(f"auth_me error: {e}")
        return {"Error": str(e)}


def dashboard_ui(resume_id: int | None = None) -> dict:
    try:
        return _run_async(dashboard(int(resume_id) if resume_id else None))
    except Exception as e:
        logger.error(f"dashboard error: {e}")
        return {"Error": str(e)}


def pipeline_apply_ui(
    resume_file: str, job_text: str, company_name: str, hiring_manager: str, format_type: str
) -> tuple[str, str, dict, dict, str | None, str | None]:
    """Returns: (tailored, cover, analysis, gaps, dl_tailored, dl_cover)"""
    if not resume_file:
        return "No file uploaded", "", {}, {}, None, None
    if not job_text or not job_text.strip():
        return "No job description", "", {}, {}, None, None
    try:
        result = _run_async(
            pipeline_apply(resume_file, job_text, company_name, hiring_manager, format_type)
        )
        if isinstance(result, dict) and "Error" in result:
            return str(result["Error"]), "", {}, {}, None, None

        tailored = result.get("tailored_content", "")
        cover = result.get("cover_letter", "")
        analysis = {
            "overall_score": result.get("overall_score", 0),
            "strengths": result.get("strengths", []),
            "suggestions": result.get("suggestions", []),
            "application_id": result.get("application_id"),
        }
        skill_gap = {
            "gaps": result.get("gaps", []),
            "strengths": result.get("strengths", []),
            "score": result.get("overall_score", 0),
        }
        return tailored, cover, analysis, skill_gap, None, None
    except Exception as e:
        logger.error(f"pipeline_apply error: {e}")
        return str(e), "", {}, {}, None, None


def discovery_search_ui(query: str, location: str, sources: list) -> tuple[list, dict]:
    """Returns: (rows for dataframe, summary dict)"""
    if not query or not query.strip():
        return [], {"Error": "No search query"}
    try:
        result = _run_async(discovery_search(query, location, sources))
        if isinstance(result, dict) and "Error" in result:
            return [], result

        rows = []
        all_jobs = result.get("results", {})
        for source, jobs in all_jobs.items():
            for j in jobs:
                rows.append([
                    j.get("title", ""),
                    j.get("company", ""),
                    j.get("location", ""),
                    source,
                    j.get("url", ""),
                ])
        summary = {
            "total": result.get("total", 0),
            "by_source": result.get("by_source", {}),
        }
        return rows, summary
    except Exception as e:
        logger.error(f"discovery_search error: {e}")
        return [], {"Error": str(e)}


def discovery_index_ui(query: str, location: str, sources: list) -> dict:
    """Search + index all discovered jobs."""
    if not query or not query.strip():
        return {"Error": "No search query"}
    try:
        search_result = _run_async(discovery_search(query, location, sources))
        if isinstance(search_result, dict) and "Error" in search_result:
            return search_result

        all_jobs = []
        for source_jobs in search_result.get("results", {}).values():
            all_jobs.extend(source_jobs)

        if not all_jobs:
            return {"message": "No jobs found to index"}

        index_result = _run_async(discovery_index(all_jobs))
        return index_result
    except Exception as e:
        logger.error(f"discovery_index error: {e}")
        return {"Error": str(e)}


# --- Gradio UI ---
with gr.Blocks(title="Job_Booster - AI Job Search Platform") as app:
    gr.Markdown(
        """
        # Job_Booster
        ### AI-Powered Job Search Platform

        Upload your resume, discover jobs, generate application packages, and track your search.
        """
    )

    with gr.Tabs():
        # Tab 1: Dashboard (default view)
        with gr.TabItem("Dashboard"):
            with gr.Row():
                with gr.Column(scale=1):
                    dash_resume_id = gr.Number(
                        label="Resume ID (for top matches)", precision=0, value=None
                    )
                    dash_load_btn = gr.Button("Refresh Dashboard", variant="primary")
                with gr.Column(scale=3):
                    dash_output = gr.JSON(label="Dashboard")

            dash_load_btn.click(
                fn=dashboard_ui,
                inputs=[dash_resume_id],
                outputs=[dash_output],
            )

        # Tab 2: Apply (unified pipeline)
        with gr.TabItem("Apply"):
            gr.Markdown("### Generate Full Application Package")
            gr.Markdown(
                "Upload resume + paste job description → get tailored resume, "
                "cover letter, match score, and skill gaps in one click."
            )
            with gr.Row():
                with gr.Column():
                    apply_resume_input = gr.File(
                        label="Upload Resume",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    apply_job_input = gr.Textbox(
                        label="Job Description",
                        placeholder="Paste the job description here...",
                        lines=10,
                    )
                    apply_company_input = gr.Textbox(label="Company Name (optional)")
                    apply_manager_input = gr.Textbox(label="Hiring Manager (optional)")
                    apply_format_input = gr.Radio(
                        label="Output Format",
                        choices=["text", "html", "docx", "pdf", "latex"],
                        value="text",
                    )
                    apply_button = gr.Button("Generate Application Package", variant="primary")

                with gr.Column():
                    apply_tailored_output = gr.Textbox(label="Tailored Resume", lines=15)
                    apply_cover_output = gr.Textbox(label="Cover Letter", lines=15)
                    apply_analysis_output = gr.JSON(label="Match Analysis")
                    apply_skill_gap_output = gr.JSON(label="Skill Gaps")

            apply_button.click(
                fn=pipeline_apply_ui,
                inputs=[
                    apply_resume_input,
                    apply_job_input,
                    apply_company_input,
                    apply_manager_input,
                    apply_format_input,
                ],
                outputs=[
                    apply_tailored_output,
                    apply_cover_output,
                    apply_analysis_output,
                    apply_skill_gap_output,
                ],
            )

        # Tab 3: Discover Jobs
        with gr.TabItem("Discover Jobs"):
            gr.Markdown("### Search Job Boards")
            with gr.Row():
                with gr.Column(scale=2):
                    discover_query = gr.Textbox(
                        label="Search Query", placeholder="e.g., Python ML Engineer"
                    )
                    discover_location = gr.Textbox(
                        label="Location (optional)",
                        placeholder="e.g., Remote, Cairo, New York",
                    )
                    discover_sources = gr.CheckboxGroup(
                        label="Sources",
                        choices=["remoteok", "indeed", "linkedin", "wuzzuf", "adzuna"],
                        value=["remoteok"],
                    )
                    with gr.Row():
                        discover_search_btn = gr.Button("Search", variant="primary")
                        discover_index_btn = gr.Button("Search & Index All", variant="secondary")
                with gr.Column(scale=3):
                    discover_summary = gr.JSON(label="Summary")
                    discover_table = gr.Dataframe(
                        headers=["Title", "Company", "Location", "Source", "URL"],
                        interactive=False,
                    )

            discover_search_btn.click(
                fn=discovery_search_ui,
                inputs=[discover_query, discover_location, discover_sources],
                outputs=[discover_table, discover_summary],
            )
            discover_index_btn.click(
                fn=discovery_index_ui,
                inputs=[discover_query, discover_location, discover_sources],
                outputs=[discover_summary],
            )

        # Tab 4: Search
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

        # Tab 5: Startup Scanner
        with gr.TabItem("Startup Scanner"):
            from app.ui.scanner_tab import create_scanner_tab

            create_scanner_tab()

        # Tab 6: Recommendations
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

        # Tab 7: Application Tracker
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

        # Tab 8: Analytics
        with gr.TabItem("Analytics"):
            with gr.Row():
                with gr.Column():
                    analytics_button = gr.Button("Load Analytics")
                with gr.Column():
                    analytics_output = gr.JSON(label="Analytics Dashboard")

            with gr.Row():
                with gr.Column():
                    skills_button = gr.Button("Skill Trends")
                with gr.Column():
                    skills_output = gr.JSON(label="Skill Trends")

            analytics_button.click(
                fn=analytics_dashboard_ui,
                inputs=[],
                outputs=[analytics_output],
            )

            skills_button.click(
                fn=skill_trends_ui,
                inputs=[],
                outputs=[skills_output],
            )

        # Tab 9: Auth
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
        1. **Dashboard**: View your job search overview at a glance
        2. **Apply**: Full application package (tailored resume + cover letter
           + analysis) in one click
        3. **Discover Jobs**: Search Indeed, LinkedIn, Wuzzuf, RemoteOK, and Adzuna
        4. **Search**: Semantic search across your stored resumes and jobs
        5. **Startup Scanner**: Scan AI/ML startup career pages for relevant jobs
        6. **Recommendations**: Job recommendations and skill gap analysis
        7. **Application Tracker**: Track and manage job applications
        8. **Analytics**: Stats and skill trends
        9. **Auth**: Register, login, and manage your profile

        Powered by Pydantic AI + LiteLLM
        """
    )


if __name__ == "__main__":
    app.launch(server_name="0.0.0.0", server_port=8050)
