"""Gradio tab: multi-source job board search."""

import gradio as gr

from app.ui.api_client import discovery_index, discovery_search, discovery_sources
from app.ui.helpers import run_async


def build_job_boards_tab() -> None:
    gr.Markdown(
        "### Job board search\n"
        "Query external boards (RemoteOK, Indeed, LinkedIn, Wuzzuf, Adzuna). "
        "Optionally index results into your local database."
    )

    with gr.Row():
        with gr.Column(scale=2):
            discover_query = gr.Textbox(
                label="Search query",
                placeholder="e.g. backend engineer python",
            )
            discover_location = gr.Textbox(
                label="Location (optional)",
                placeholder="Remote, Cairo, NYC…",
            )
            discover_sources = gr.CheckboxGroup(
                label="Sources",
                choices=["remoteok", "indeed", "linkedin", "wuzzuf", "adzuna"],
                value=["remoteok"],
            )
            with gr.Row():
                discover_search_btn = gr.Button("Search", variant="primary")
                discover_index_btn = gr.Button("Search & index", variant="secondary")
                sources_btn = gr.Button("List sources", size="sm")
        with gr.Column(scale=3):
            discover_summary = gr.JSON(label="Summary")
            discover_table = gr.Dataframe(
                headers=["Title", "Company", "Location", "Source", "URL"],
                interactive=False,
            )

    def _rows_from_result(result: dict) -> tuple[list, dict]:
        if isinstance(result, dict) and result.get("Error"):
            return [], result
        rows = []
        for source, jobs in (result.get("results") or {}).items():
            for j in jobs:
                rows.append(
                    [
                        j.get("title", ""),
                        j.get("company", ""),
                        j.get("location", ""),
                        source,
                        j.get("url", ""),
                    ]
                )
        summary = {
            "total": result.get("total", 0),
            "by_source": result.get("by_source", {}),
        }
        return rows, summary

    def search_ui(query, location, sources):
        if not query or not str(query).strip():
            return [], {"Error": "Enter a search query"}
        try:
            result = run_async(discovery_search(query, location, sources))
            return _rows_from_result(result)
        except Exception as e:
            return [], {"Error": str(e)}

    def index_ui(query, location, sources):
        if not query or not str(query).strip():
            return {"Error": "Enter a search query"}
        try:
            search_result = run_async(discovery_search(query, location, sources))
            if isinstance(search_result, dict) and search_result.get("Error"):
                return search_result
            all_jobs = []
            for source_jobs in (search_result.get("results") or {}).values():
                all_jobs.extend(source_jobs)
            if not all_jobs:
                return {"message": "No jobs found to index"}
            return run_async(discovery_index(all_jobs))
        except Exception as e:
            return {"Error": str(e)}

    def list_sources_ui():
        try:
            return run_async(discovery_sources())
        except Exception as e:
            return {"Error": str(e)}

    discover_search_btn.click(
        fn=search_ui,
        inputs=[discover_query, discover_location, discover_sources],
        outputs=[discover_table, discover_summary],
    )
    discover_index_btn.click(
        fn=index_ui,
        inputs=[discover_query, discover_location, discover_sources],
        outputs=[discover_summary],
    )
    sources_btn.click(fn=list_sources_ui, outputs=[discover_summary])
