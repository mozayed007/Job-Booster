"""Gradio tab: imported job corpus (BigSet CSV/XLSX) and profile-ranked jobs."""

import gradio as gr

from app.ui.api_client import (
    discovery_bigset_import,
    discovery_bigset_mappings,
    discovery_bigset_preview,
    discovery_bigset_remote_status,
    discovery_bigset_remote_trigger,
    discovery_bigset_sync,
    discovery_ranked_jobs,
)
from app.ui.helpers import run_async


def _mapping_choices(data: dict) -> list[str]:
    mappings = data.get("mappings", [])
    if not mappings:
        return []
    if isinstance(mappings[0], dict):
        return [m.get("id", "") for m in mappings if m.get("id")]
    return list(mappings)


def _jobs_to_rows(jobs: list) -> tuple[list[list], list[dict]]:
    rows = []
    options = []
    for j in jobs:
        url = j.get("source_url") or j.get("url") or ""
        title = j.get("title", "")
        company = j.get("company", "")
        snippet = (j.get("snippet") or j.get("raw_text") or "")[:2000]
        rows.append(
            [
                title,
                company,
                j.get("location", ""),
                f"{j.get('fit_score', j.get('score', 0)):.2f}"
                if isinstance(j.get("fit_score", j.get("score", 0)), (int, float))
                else str(j.get("fit_score", "")),
                url[:80],
            ]
        )
        options.append(
            {
                "label": f"{title} @ {company}",
                "title": title,
                "company": company,
                "url": url,
                "snippet": snippet,
            }
        )
    return rows, options


def build_discovery_corpus_tab(api_token, selected_job_text) -> tuple:
    """Add BigSet import / sync / ranked jobs UI into the current Blocks context."""
    gr.Markdown(
        "### Imported job corpus\n"
        "Import CSV/XLSX exports (BigSet or manual), sync the watch folder, "
        "and browse jobs ranked against your profile."
    )

    with gr.Accordion("Remote BigSet (optional)", open=False):
        remote_status_btn = gr.Button("Load remote status", size="sm")
        remote_status_json = gr.JSON(label="Remote config")
        remote_goal_md = gr.Markdown("")
        force_remote_cb = gr.Checkbox(label="Force remote trigger", value=False)
        remote_trigger_btn = gr.Button("Trigger remote dataset build")
        remote_result = gr.JSON(label="Remote result")

    with gr.Row():
        with gr.Column(scale=2):
            import_file = gr.File(
                label="Upload CSV or XLSX",
                file_types=[".csv", ".xlsx", ".xls"],
            )
            mapping_dropdown = gr.Dropdown(
                label="Column mapping profile",
                choices=[],
                value=None,
                allow_custom_value=True,
            )
            with gr.Row():
                refresh_mappings_btn = gr.Button("Refresh mappings", size="sm")
                preview_btn = gr.Button("Preview mapping")
                import_btn = gr.Button("Import file", variant="primary")
                sync_folder_btn = gr.Button("Sync import folder", variant="secondary")

            preview_result = gr.JSON(label="Preview (column match)")
            import_result = gr.JSON(label="Import result")
            can_import_state = gr.State(value=True)

        with gr.Column(scale=3):
            gr.Markdown("#### Ranked jobs (profile fit)")
            with gr.Row():
                ranked_limit = gr.Slider(5, 100, value=25, step=5, label="Limit")
                ranked_min_score = gr.Slider(
                    0, 1, value=0.0, step=0.05, label="Min fit score (0 = profile default)"
                )
                ranked_query = gr.Textbox(
                    label="Semantic filter (optional)",
                    placeholder="e.g. remote backend python",
                    scale=2,
                )
            ranked_btn = gr.Button("Load ranked jobs", variant="primary")
            ranked_table = gr.Dataframe(
                headers=["Title", "Company", "Location", "Fit", "URL"],
                datatype=["str", "str", "str", "str", "str"],
                interactive=False,
            )
            ranked_job_pick = gr.Dropdown(label="Select job for Apply tab", choices=[])
            use_in_apply_btn = gr.Button("Open in Apply tab")
            ranked_summary = gr.JSON(label="Summary")
            ranked_jobs_state = gr.State(value=[])

    def load_mappings():
        try:
            data = run_async(discovery_bigset_mappings())
            ids = _mapping_choices(data)
            if not ids:
                return gr.Dropdown(choices=[], value=None)
            return gr.Dropdown(choices=ids, value=ids[0])
        except Exception as e:
            return gr.Dropdown(choices=[], value=None, info=str(e))

    def _file_path(file_obj):
        if file_obj is None:
            return None
        return getattr(file_obj, "name", None) or (file_obj if isinstance(file_obj, str) else None)

    def do_preview(file_obj, mapping_id, token):
        if not token or not str(token).strip():
            return {"Error": "Sign in first"}, True
        path = _file_path(file_obj)
        if not path:
            return {"Error": "Choose a file"}, True
        try:
            data = run_async(discovery_bigset_preview(token, path, mapping_id))
            if data.get("Error"):
                return data, True
            can = data.get("can_import", True)
            return data, can
        except Exception as e:
            return {"Error": str(e)}, True

    def do_import(file_obj, mapping_id, token, can_import):
        if not can_import:
            return {"Error": "Fix missing columns in Preview before importing"}
        if not token or not str(token).strip():
            return {"Error": "Sign in on the Account tab first"}
        path = _file_path(file_obj)
        if not path:
            return {"Error": "Choose a file to upload"}
        try:
            return run_async(discovery_bigset_import(token, path, mapping_id))
        except Exception as e:
            return {"Error": str(e)}

    def do_sync(token):
        if not token or not str(token).strip():
            return {"Error": "Sign in on the Account tab first"}
        try:
            return run_async(discovery_bigset_sync(token))
        except Exception as e:
            return {"Error": str(e)}

    def load_ranked(limit, min_score, query, token):
        if not token or not str(token).strip():
            return [], {"Error": "Sign in first"}, gr.Dropdown(choices=[]), []
        try:
            ms = float(min_score) if min_score and float(min_score) > 0 else None
            data = run_async(
                discovery_ranked_jobs(
                    token,
                    limit=int(limit),
                    min_score=ms,
                    query=query or "",
                )
            )
            if isinstance(data, dict) and data.get("Error"):
                return [], data, gr.Dropdown(choices=[]), []
            jobs = data.get("jobs", [])
            rows, options = _jobs_to_rows(jobs)
            choices = [o["label"] for o in options]
            return (
                rows,
                {"count": data.get("count", len(jobs)), "query": query or None},
                gr.Dropdown(choices=choices, value=choices[0] if choices else None),
                options,
            )
        except Exception as e:
            return [], {"Error": str(e)}, gr.Dropdown(choices=[]), []

    def use_in_apply(label, options):
        if not label or not options:
            return ""
        for o in options:
            if o.get("label") == label:
                parts = [
                    f"Title: {o.get('title', '')}",
                    f"Company: {o.get('company', '')}",
                    f"URL: {o.get('url', '')}",
                    "",
                    o.get("snippet", ""),
                ]
                return "\n".join(parts).strip()
        return ""

    def load_remote_status(token):
        if not token:
            return {"Error": "Sign in first"}, ""
        try:
            data = run_async(discovery_bigset_remote_status(token))
            goal = data.get("cached_goal", "")
            md = f"**Cached dataset goal:**\n\n{goal}" if goal else "_No cached goal yet._"
            return data, md
        except Exception as e:
            return {"Error": str(e)}, ""

    def trigger_remote(token, force):
        if not token:
            return {"Error": "Sign in first"}
        try:
            return run_async(discovery_bigset_remote_trigger(token, force=bool(force)))
        except Exception as e:
            return {"Error": str(e)}

    refresh_mappings_btn.click(fn=load_mappings, outputs=[mapping_dropdown])
    preview_btn.click(
        fn=do_preview,
        inputs=[import_file, mapping_dropdown, api_token],
        outputs=[preview_result, can_import_state],
    )
    import_btn.click(
        fn=do_import,
        inputs=[import_file, mapping_dropdown, api_token, can_import_state],
        outputs=[import_result],
    )
    sync_folder_btn.click(fn=do_sync, inputs=[api_token], outputs=[import_result])
    ranked_btn.click(
        fn=load_ranked,
        inputs=[ranked_limit, ranked_min_score, ranked_query, api_token],
        outputs=[ranked_table, ranked_summary, ranked_job_pick, ranked_jobs_state],
    )
    use_in_apply_btn.click(
        fn=use_in_apply,
        inputs=[ranked_job_pick, ranked_jobs_state],
        outputs=[selected_job_text],
    )
    remote_status_btn.click(
        fn=load_remote_status,
        inputs=[api_token],
        outputs=[remote_status_json, remote_goal_md],
    )
    remote_trigger_btn.click(
        fn=trigger_remote,
        inputs=[api_token, force_remote_cb],
        outputs=[remote_result],
    )

    return mapping_dropdown, load_mappings
