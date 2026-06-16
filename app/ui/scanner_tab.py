"""Gradio Startup Scanner tab — career-page batch scanning."""

import gradio as gr

from app.ui.api_client import (
    scanner_cities,
    scanner_progress,
    scanner_reset,
    scanner_scan_batch,
    scanner_top_jobs,
)
from app.ui.helpers import run_async


def _progress_markdown(progress: dict) -> str:
    total = progress.get("total_startups", 0)
    websites = progress.get("with_websites", 0)
    processed = progress.get("processed", 0)
    remaining = progress.get("remaining", 0)
    jobs = progress.get("promising_roles", 0)
    pct = (processed / max(websites, 1)) * 100
    return (
        f"**Companies:** {total}  \n"
        f"**With career URLs:** {websites}  \n"
        f"**Processed:** {processed} ({pct:.1f}%)  \n"
        f"**Remaining:** {remaining}  \n"
        f"**Matching roles found:** {jobs}  \n"
        f"**Status:** {progress.get('status', 'idle')}"
    )


def _jobs_rows(jobs: list) -> list[list]:
    rows = []
    for j in jobs:
        if isinstance(j, dict):
            rows.append(
                [
                    j.get("startup_name", j.get("company", "")),
                    j.get("title", ""),
                    j.get("location", ""),
                    f"{j.get('relevance_score', j.get('fit_score', 0)):.2f}",
                ]
            )
        else:
            rows.append([getattr(j, "startup_name", ""), getattr(j, "title", ""), "", ""])
    return rows


def build_scanner_tab() -> tuple:
    """Add scanner components to the current Gradio Blocks context (no nested Blocks)."""
    gr.Markdown(
        "### Company scanner\n"
        "Batch-scan career pages from your startup list (`data/startups/startups.md`) "
        "and surface roles that match your profile."
    )

    with gr.Row():
        with gr.Column(scale=2):
            progress_text = gr.Markdown("Loading…")
            with gr.Row():
                batch_size = gr.Slider(1, 20, value=5, step=1, label="Batch size")
                scan_btn = gr.Button("Scan next batch", variant="primary")
                reset_btn = gr.Button("Reset scanner", variant="secondary")
                refresh_btn = gr.Button("Refresh", size="sm")

            jobs_table = gr.Dataframe(
                headers=["Company", "Title", "Location", "Score"],
                datatype=["str", "str", "str", "str"],
                interactive=False,
            )

        with gr.Column(scale=1):
            stats_json = gr.JSON(label="Progress JSON")
            city_dropdown = gr.Dropdown(
                label="City filter (display)",
                choices=["All"],
                value="All",
                interactive=True,
            )

    def refresh_state(city="All"):
        try:
            progress = run_async(scanner_progress())
            rows = _jobs_rows(run_async(scanner_top_jobs(50, city=city)))
            cities_data = run_async(scanner_cities())
            if isinstance(cities_data, dict):
                city_choices = ["All"] + list(cities_data.keys())
            else:
                city_choices = ["All"]
            return (
                _progress_markdown(progress),
                progress,
                rows,
                gr.Dropdown(choices=city_choices, value="All"),
            )
        except Exception as e:
            err_row = [[str(e), "", "", ""]]
            dd = gr.Dropdown(choices=["All"], value="All")
            return f"**Error:** {e}", {}, err_row, dd

    def scan_batch(size):
        try:
            result = run_async(scanner_scan_batch(int(size)))
            progress = result.get("progress", result)
            if not progress and "total_startups" in result:
                progress = result
            jobs = result.get("jobs", [])
            if jobs:
                rows = _jobs_rows(jobs)
            else:
                rows = _jobs_rows(run_async(scanner_top_jobs(50, city="All")))
            return _progress_markdown(progress), progress, rows
        except Exception as e:
            return f"**Error:** {e}", {}, [[str(e), "", "", ""]]

    def reset():
        try:
            run_async(scanner_reset())
            return refresh_state()[:3]
        except Exception as e:
            return f"**Error:** {e}", {}, [[str(e), "", "", ""]]

    scan_btn.click(
        fn=scan_batch,
        inputs=[batch_size],
        outputs=[progress_text, stats_json, jobs_table],
    )
    reset_btn.click(fn=reset, outputs=[progress_text, stats_json, jobs_table])
    refresh_btn.click(
        fn=refresh_state,
        inputs=[city_dropdown],
        outputs=[progress_text, stats_json, jobs_table, city_dropdown],
    )
    city_dropdown.change(
        fn=lambda city: refresh_state(city)[:3],
        inputs=[city_dropdown],
        outputs=[progress_text, stats_json, jobs_table],
    )

    return progress_text, stats_json, jobs_table, city_dropdown, refresh_state
