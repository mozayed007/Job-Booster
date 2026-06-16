"""Gradio UI shell for Job_Booster."""

import os

import gradio as gr
from loguru import logger

from app.ui.api_client import (
    analytics_dashboard,
    application_stats,
    dashboard,
    health_check,
    list_applications,
    pipeline_apply,
    recommend_jobs,
    recommend_resumes,
    search,
    skill_gap,
    skill_trends,
    track_application,
)
from app.ui.auth_tab import build_auth_tab
from app.ui.discovery_tab import build_discovery_corpus_tab
from app.ui.helpers import run_async
from app.ui.job_boards_tab import build_job_boards_tab
from app.ui.pipelines_tab import build_pipelines_tab
from app.ui.scanner_tab import build_scanner_tab

logger.info("Initializing Job_Booster UI")


def _err(msg: str) -> dict:
    return {"Error": msg}


def dashboard_ui(resume_id):
    try:
        rid = int(resume_id) if resume_id else None
        return run_async(dashboard(rid))
    except Exception as e:
        logger.error("dashboard: {}", e)
        return _err(str(e))


def api_status_ui():
    try:
        return run_async(health_check())
    except Exception as e:
        return {"ok": False, "Error": str(e)}


def pipeline_apply_ui(resume_file, job_text, company_name, hiring_manager, format_type):
    if not resume_file:
        return "Upload a resume file", "", {}, {}
    if not job_text or not str(job_text).strip():
        return "Paste a job description", "", {}, {}
    try:
        result = run_async(
            pipeline_apply(resume_file, job_text, company_name, hiring_manager, format_type)
        )
        if isinstance(result, dict) and result.get("Error"):
            return str(result["Error"]), "", {}, {}
        return (
            result.get("tailored_content", ""),
            result.get("cover_letter", ""),
            {
                "overall_score": result.get("overall_score", 0),
                "strengths": result.get("strengths", []),
                "suggestions": result.get("suggestions", []),
                "application_id": result.get("application_id"),
            },
            {"gaps": result.get("gaps", []), "score": result.get("overall_score", 0)},
        )
    except Exception as e:
        logger.error("pipeline_apply: {}", e)
        return str(e), "", {}, {}


def search_ui(query, collection, n_results):
    if not query or not str(query).strip():
        return _err("Enter a search query")
    try:
        return run_async(search(query, collection, int(n_results)))
    except Exception as e:
        return _err(str(e))


def recommend_jobs_ui(resume_id):
    try:
        return run_async(recommend_jobs(int(resume_id)))
    except Exception as e:
        return _err(str(e))


def recommend_resumes_ui(job_id):
    try:
        return run_async(recommend_resumes(int(job_id)))
    except Exception as e:
        return _err(str(e))


def skill_gap_ui(resume_id, job_id):
    try:
        return run_async(skill_gap(int(resume_id), int(job_id)))
    except Exception as e:
        return _err(str(e))


def track_application_ui(company, position, status, notes):
    if not company or not position:
        return _err("Company and position are required")
    try:
        return run_async(track_application(company, position, status, notes))
    except Exception as e:
        return _err(str(e))


def list_applications_ui():
    try:
        result = run_async(list_applications())
        return result if isinstance(result, list) else [result]
    except Exception as e:
        return [_err(str(e))]


def application_stats_ui():
    try:
        return run_async(application_stats())
    except Exception as e:
        return _err(str(e))


def analytics_dashboard_ui():
    try:
        return run_async(analytics_dashboard())
    except Exception as e:
        return _err(str(e))


def skill_trends_ui():
    try:
        return run_async(skill_trends())
    except Exception as e:
        return _err(str(e))


with gr.Blocks(title="Job Booster") as app:
    api_token = gr.State(value="")
    selected_job_text = gr.State(value="")

    gr.Markdown(
        """
        # Job Booster
        Profile-driven job discovery: import corpora, scan company sites,
        rank fit, and generate application packages.
        """
    )

    with gr.Row():
        api_status = gr.JSON(label="API status", scale=1)
        gr.Button("Check API", size="sm", scale=0).click(fn=api_status_ui, outputs=[api_status])

    with gr.Tabs():
        with gr.Tab("Overview"):
            with gr.Row():
                dash_resume_id = gr.Number(label="Resume ID (optional)", precision=0)
                dash_load_btn = gr.Button("Refresh dashboard", variant="primary")
            dash_output = gr.JSON(label="Dashboard")
            dash_load_btn.click(fn=dashboard_ui, inputs=[dash_resume_id], outputs=[dash_output])

        with gr.Tab("Apply"):
            gr.Markdown(
                "Upload a resume and paste a job description to get a tailored resume, "
                "cover letter, match analysis, and skill gaps in one request."
            )
            with gr.Row():
                with gr.Column():
                    apply_resume = gr.File(
                        label="Resume",
                        file_types=[".pdf", ".docx", ".md", ".txt", ".tex"],
                    )
                    paste_ranked_btn = gr.Button("Paste job from Discovery tab", size="sm")
                    apply_job = gr.Textbox(label="Job description", lines=10)
                    apply_company = gr.Textbox(label="Company (optional)")
                    apply_manager = gr.Textbox(label="Hiring manager (optional)")
                    apply_format = gr.Radio(
                        label="Format",
                        choices=["text", "html", "docx", "pdf", "latex"],
                        value="text",
                    )
                    apply_btn = gr.Button("Generate package", variant="primary")
                with gr.Column():
                    apply_tailored = gr.Textbox(label="Tailored resume", lines=14)
                    apply_cover = gr.Textbox(label="Cover letter", lines=14)
                    apply_analysis = gr.JSON(label="Match analysis")
                    apply_gaps = gr.JSON(label="Skill gaps")

            def paste_job_from_discovery(text):
                return text or ""

            paste_ranked_btn.click(
                fn=paste_job_from_discovery,
                inputs=[selected_job_text],
                outputs=[apply_job],
            )
            apply_btn.click(
                fn=pipeline_apply_ui,
                inputs=[apply_resume, apply_job, apply_company, apply_manager, apply_format],
                outputs=[apply_tailored, apply_cover, apply_analysis, apply_gaps],
            )

        with gr.Tab("Discovery"):
            with gr.Tabs():
                with gr.Tab("Imported corpus"):
                    _map_dd, load_map_fn = build_discovery_corpus_tab(api_token, selected_job_text)
                    app.load(fn=load_map_fn, outputs=[_map_dd])
                with gr.Tab("Job boards"):
                    build_job_boards_tab()

        with gr.Tab("Pipelines"):
            pipe_dd, pipe_refresh = build_pipelines_tab(api_token)
            app.load(fn=pipe_refresh, outputs=[pipe_dd])

        with gr.Tab("Scanner"):
            scan_prog, scan_stats, scan_jobs, scan_cities, scan_refresh = build_scanner_tab()
            app.load(
                fn=scan_refresh,
                outputs=[scan_prog, scan_stats, scan_jobs, scan_cities],
            )

        with gr.Tab("Search"):
            with gr.Row():
                with gr.Column():
                    search_query = gr.Textbox(
                        label="Query",
                        placeholder="Skills, titles, companies…",
                    )
                    search_collection = gr.Radio(
                        label="Collection",
                        choices=["resumes", "jobs"],
                        value="jobs",
                    )
                    search_n = gr.Slider(1, 20, value=5, step=1, label="Results")
                    search_btn = gr.Button("Search")
                with gr.Column():
                    search_output = gr.JSON(label="Results")
            search_btn.click(
                fn=search_ui,
                inputs=[search_query, search_collection, search_n],
                outputs=[search_output],
            )

        with gr.Tab("Recommendations"):
            with gr.Row():
                with gr.Column():
                    rec_resume_id = gr.Number(label="Resume ID", precision=0)
                    rec_jobs_btn = gr.Button("Recommend jobs")
                    rec_jobs_out = gr.JSON(label="Jobs")
                with gr.Column():
                    rec_job_id = gr.Number(label="Job ID", precision=0)
                    rec_resumes_btn = gr.Button("Recommend resumes")
                    rec_resumes_out = gr.JSON(label="Resumes")
            with gr.Row():
                sg_resume = gr.Number(label="Resume ID", precision=0)
                sg_job = gr.Number(label="Job ID", precision=0)
                sg_btn = gr.Button("Skill gap")
                sg_out = gr.JSON(label="Gap analysis")
            rec_jobs_btn.click(fn=recommend_jobs_ui, inputs=[rec_resume_id], outputs=[rec_jobs_out])
            rec_resumes_btn.click(
                fn=recommend_resumes_ui, inputs=[rec_job_id], outputs=[rec_resumes_out]
            )
            sg_btn.click(fn=skill_gap_ui, inputs=[sg_resume, sg_job], outputs=[sg_out])

        with gr.Tab("Applications"):
            with gr.Row():
                with gr.Column():
                    app_company = gr.Textbox(label="Company")
                    app_position = gr.Textbox(label="Position")
                    app_status = gr.Dropdown(
                        label="Status",
                        choices=["applied", "interview", "offer", "rejected", "withdrawn"],
                        value="applied",
                    )
                    app_notes = gr.Textbox(label="Notes", lines=3)
                    track_btn = gr.Button("Track application")
                    track_out = gr.JSON(label="Last tracked")
                with gr.Column():
                    view_btn = gr.Button("List applications")
                    stats_btn = gr.Button("Stats")
                    apps_table = gr.Dataframe(
                        headers=["company_name", "position_title", "status", "notes"],
                        interactive=False,
                    )
                    apps_stats = gr.JSON(label="Stats")
            track_btn.click(
                fn=track_application_ui,
                inputs=[app_company, app_position, app_status, app_notes],
                outputs=[track_out],
            )
            view_btn.click(fn=list_applications_ui, outputs=[apps_table])
            stats_btn.click(fn=application_stats_ui, outputs=[apps_stats])

        with gr.Tab("Analytics"):
            with gr.Row():
                analytics_btn = gr.Button("Dashboard")
                analytics_out = gr.JSON(label="Analytics")
                skills_btn = gr.Button("Skill trends")
                skills_out = gr.JSON(label="Trends")
            analytics_btn.click(fn=analytics_dashboard_ui, outputs=[analytics_out])
            skills_btn.click(fn=skill_trends_ui, outputs=[skills_out])

        with gr.Tab("Account"):
            build_auth_tab(api_token)

    gr.Markdown(
        """
        ---
        **Tips:** Configure targets in `data/user_profile.yaml`. Drop BigSet exports in
        `data/bigset_imports/` and use **Discovery → Imported corpus → Sync import folder**.
        API docs: [http://localhost:8000/docs](http://localhost:8000/docs)
        """
    )

    app.load(fn=api_status_ui, outputs=[api_status])


if __name__ == "__main__":
    app.launch(
        server_name=os.getenv("GRADIO_SERVER_NAME", "127.0.0.1"),
        server_port=int(os.getenv("GRADIO_SERVER_PORT", "8050")),
        theme=gr.themes.Soft(primary_hue="slate"),
    )
