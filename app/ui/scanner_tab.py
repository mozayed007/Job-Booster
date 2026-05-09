"""Gradio Startup Scanner Tab - UI for scanning startup career pages."""

import os

import gradio as gr
import httpx

API_URL = os.getenv("API_URL", "http://localhost:8000")


def create_scanner_tab() -> gr.Blocks:
    """Create the Gradio tab for startup scanning."""

    with gr.Blocks() as scanner_tab:
        gr.Markdown("# Startup Job Scanner")
        gr.Markdown("Scan AI/ML startup career pages to find relevant job openings.")

        with gr.Row():
            with gr.Column(scale=2):
                with gr.Group():
                    gr.Markdown("### Scanning Progress")
                    progress_text = gr.Markdown("Loading progress...")

                with gr.Row():
                    batch_size = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1, label="Batch Size"
                    )
                    scan_btn = gr.Button("Scan Next Batch", variant="primary")
                    reset_btn = gr.Button("Reset", variant="secondary")

                gr.Markdown("### Found Jobs")
                jobs_table = gr.Dataframe(
                    headers=["Startup", "Title", "Location", "Score"],
                    datatype=["str", "str", "str", "str"],
                    interactive=False,
                )

            with gr.Column(scale=1):
                gr.Markdown("### Statistics")
                stats_json = gr.JSON(label="Current Stats")

                gr.Markdown("### Cities")
                _city_dropdown = gr.Dropdown(
                    label="Filter by City",
                    choices=["All"],
                    value="All",
                    interactive=True,
                )

        def get_progress():
            try:
                resp = httpx.get(f"{API_URL}/api/scanner/progress", timeout=10.0)
                progress = resp.json()
                total = progress.get("total_startups", 0)
                websites = progress.get("with_websites", 0)
                processed = progress.get("processed", 0)
                remaining = progress.get("remaining", 0)
                jobs = progress.get("promising_roles", 0)
                pct = (processed / max(websites, 1)) * 100

                progress_md = (
                    f"**Total Startups:** {total}  \n"
                    f"**With Websites:** {websites}  \n"
                    f"**Processed:** {processed} ({pct:.1f}%)  \n"
                    f"**Remaining:** {remaining}  \n"
                    f"**Jobs Found:** {jobs}  \n"
                    f"**Status:** {progress.get('status', 'idle')}"
                )
                return progress_md, progress
            except Exception as e:
                return f"Error: {e}", {}

        def get_jobs():
            try:
                resp = httpx.get(f"{API_URL}/api/scanner/jobs/top", params={"limit": 50}, timeout=10.0)
                data = resp.json()
                jobs = data.get("jobs", [])
                return [[j.get("startup_name", ""), j.get("title", ""), j.get("location", ""), f"{j.get('relevance_score', 0):.2f}"] for j in jobs]
            except Exception as e:
                return [[str(e), "", "", ""]]

        def scan_batch(size):
            try:
                resp = httpx.post(
                    f"{API_URL}/api/scanner/scan/batch",
                    json={"batch_size": int(size)},
                    timeout=300.0,
                )
                result = resp.json()
                if not result.get("success"):
                    return f"Error: {result.get('message', 'Unknown')}", {}, []
                progress_md, stats = get_progress()
                jobs_data = get_jobs()
                return progress_md, stats, jobs_data
            except Exception as e:
                return f"Error: {e}", {}, []

        def reset_scanner():
            try:
                httpx.post(f"{API_URL}/api/scanner/reset", timeout=10.0)
                progress_md, stats = get_progress()
                jobs_data = get_jobs()
                return progress_md, stats, jobs_data
            except Exception as e:
                return f"Error: {e}", {}, []

        scan_btn.click(
            fn=scan_batch,
            inputs=[batch_size],
            outputs=[progress_text, stats_json, jobs_table],
        )

        reset_btn.click(
            fn=reset_scanner,
            outputs=[progress_text, stats_json, jobs_table],
        )

        scanner_tab.load(
            fn=lambda: (*get_progress(), get_jobs()),
            outputs=[progress_text, stats_json, jobs_table],
        )

    return scanner_tab


if __name__ == "__main__":
    demo = create_scanner_tab()
    demo.launch()
