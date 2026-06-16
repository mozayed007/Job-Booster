"""Gradio tab: run agent pipelines on demand."""

import time

import gradio as gr

from app.core.config import settings
from app.ui.api_client import pipeline_list, pipeline_run, pipeline_run_status
from app.ui.helpers import run_async

_TEXT_PIPELINES = frozenset(
    {
        "full_application",
        "resume_only",
        "job_search_only",
        "cover_letter_only",
        "outreach",
        "interview_prep",
    }
)
_SYNC_PIPELINES = frozenset({"discovery_sync_only", "daily_scanner"})


def _poll_background_job(token: str, job_id: str) -> dict:
    """Poll until completed, failed, or timeout."""
    interval = settings.PIPELINE_UI_POLL_INTERVAL_SECONDS
    max_attempts = settings.PIPELINE_UI_POLL_MAX_ATTEMPTS
    status: dict = {"status": "running", "job_id": job_id}
    for _ in range(max_attempts):
        status = run_async(pipeline_run_status(token, job_id.strip()))
        if status.get("status") in ("completed", "failed"):
            return status
        if status.get("Error"):
            return status
        time.sleep(interval)
    status.setdefault(
        "message",
        f"Still running after {max_attempts * interval:.0f}s; use Poll to check again.",
    )
    return status


def build_pipelines_tab(api_token) -> tuple:
    gr.Markdown(
        "### Agent pipelines\n"
        "Run configured pipelines from `app/pipelines/pipelines.yaml`. "
        "Use **discovery_sync_only** after dropping files in `data/bigset_imports/`."
    )

    pipeline_dropdown = gr.Dropdown(label="Pipeline", choices=[], value=None)
    refresh_list_btn = gr.Button("Refresh list", size="sm")
    force_remote = gr.Checkbox(
        label="Force remote BigSet dataset request",
        value=False,
    )
    resume_text = gr.Textbox(label="Resume text (optional)", lines=6, visible=False)
    job_text = gr.Textbox(label="Job description (optional)", lines=6, visible=False)
    run_background = gr.Checkbox(
        label="Run in background (long LLM pipelines)",
        value=False,
    )
    run_btn = gr.Button("Run pipeline", variant="primary")
    poll_btn = gr.Button("Poll background job", visible=False)
    job_id_box = gr.Textbox(label="Background job ID", visible=False, interactive=False)
    result_json = gr.JSON(label="Pipeline result")

    def refresh_list():
        try:
            data = run_async(pipeline_list())
            pipelines = data.get("pipelines", [])
            keys = [p["key"] for p in pipelines]
            return gr.Dropdown(choices=keys, value=keys[0] if keys else None)
        except Exception as e:
            return gr.Dropdown(choices=[], value=None, info=str(e))

    def toggle_inputs(key):
        show = key in _TEXT_PIPELINES
        return (
            gr.Textbox(visible=show),
            gr.Textbox(visible=show),
            gr.Checkbox(value=key not in _SYNC_PIPELINES),
        )

    def run_pipeline(key, resume, job, force, bg, token):
        if not token or not str(token).strip():
            return {"Error": "Sign in on the Account tab first"}, "", gr.Button(visible=False)
        if not key:
            return {"Error": "Select a pipeline"}, "", gr.Button(visible=False)
        inputs = {}
        if force:
            inputs["force_remote"] = True
        try:
            out = run_async(
                pipeline_run(
                    token,
                    key,
                    resume_text=resume or "",
                    job_text=job or "",
                    inputs=inputs,
                    background=bool(bg),
                )
            )
            if out.get("status") == "accepted" and out.get("job_id"):
                job_id = out["job_id"]
                status = _poll_background_job(token, job_id)
                still_running = status.get("status") == "running"
                return status, job_id, gr.Button(visible=still_running)
            return out, "", gr.Button(visible=False)
        except Exception as e:
            return {"Error": str(e)}, "", gr.Button(visible=False)

    def poll_job(job_id, token):
        if not job_id or not token:
            return {"Error": "Need job ID and token"}
        try:
            return _poll_background_job(token, job_id)
        except Exception as e:
            return {"Error": str(e)}

    refresh_list_btn.click(fn=refresh_list, outputs=[pipeline_dropdown])
    pipeline_dropdown.change(
        fn=toggle_inputs,
        inputs=[pipeline_dropdown],
        outputs=[resume_text, job_text, run_background],
    )
    run_btn.click(
        fn=run_pipeline,
        inputs=[pipeline_dropdown, resume_text, job_text, force_remote, run_background, api_token],
        outputs=[result_json, job_id_box, poll_btn],
    )
    poll_btn.click(fn=poll_job, inputs=[job_id_box, api_token], outputs=[result_json])

    return pipeline_dropdown, refresh_list
