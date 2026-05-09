"""Gradio Startup Scanner Tab - UI for scanning startup career pages."""

import asyncio

import gradio as gr

try:
    import nest_asyncio

    nest_asyncio.apply()
except ImportError:
    pass


def create_scanner_tab() -> gr.Blocks:
    """Create the Gradio tab for startup scanning."""

    with gr.Blocks() as scanner_tab:
        gr.Markdown("# 🔍 Startup Job Scanner")
        gr.Markdown("Scan AI/ML startup career pages to find relevant job openings.")

        with gr.Row():
            with gr.Column(scale=2):
                # Progress Section
                with gr.Group():
                    gr.Markdown("### 📊 Scanning Progress")
                    progress_text = gr.Markdown("Loading progress...")

                # Controls
                with gr.Row():
                    batch_size = gr.Slider(
                        minimum=1, maximum=20, value=5, step=1, label="Batch Size"
                    )
                    scan_btn = gr.Button("🚀 Scan Next Batch", variant="primary")
                    reset_btn = gr.Button("🔄 Reset", variant="secondary")

                # Results
                gr.Markdown("### 💼 Found Jobs")
                jobs_table = gr.Dataframe(
                    headers=["Startup", "Title", "Location", "Score"],
                    datatype=["str", "str", "str", "number"],
                    interactive=False,
                )

            with gr.Column(scale=1):
                # Stats
                gr.Markdown("### 📈 Statistics")
                stats_json = gr.JSON(label="Current Stats")

                # City filter
                gr.Markdown("### 🌍 Cities")
                _city_dropdown = gr.Dropdown(
                    label="Filter by City",
                    choices=["All"],
                    value="All",
                    interactive=True,
                )

        # Event handlers
        def get_progress():
            """Get current scanning progress."""
            try:
                from app.agents.startup_scanner import StartupScannerAgent

                agent = StartupScannerAgent()
                progress = agent.get_progress()

                progress_md = f"""
**Total Startups:** {progress["total_startups"]}  
**With Websites:** {progress["with_websites"]}  
**Processed:** {progress["processed"]} ({(progress["processed"] / max(progress["with_websites"], 1) * 100):.1f}%)  
**Remaining:** {progress["remaining"]}  
**Jobs Found:** {progress["promising_roles"]}  
**Status:** {progress["status"]}
"""
                return progress_md, progress
            except Exception as e:
                return f"Error: {e}", {}

        def get_jobs():
            """Get top jobs as dataframe."""
            try:
                from app.agents.startup_scanner import StartupScannerAgent

                agent = StartupScannerAgent()
                jobs = agent.get_top_roles(limit=50)

                data = [
                    [j.startup_name, j.title, j.location, f"{j.relevance_score:.2f}"] for j in jobs
                ]
                return data
            except Exception as e:
                return [[str(e), "", "", ""]]

        def scan_batch(size):
            """Run a scanning batch."""
            try:
                from app.agents.startup_scanner import StartupScannerAgent

                agent = StartupScannerAgent()

                # Run async function
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(agent.process_batch(batch_size=int(size)))
                loop.close()

                # Return updated data
                progress_md, stats = get_progress()
                jobs_data = get_jobs()

                return progress_md, stats, jobs_data
            except Exception as e:
                return f"Error: {e}", {}, []

        def reset_scanner():
            """Reset the scanner state."""
            try:
                from pathlib import Path

                state_file = Path("scanner_state.json")
                if state_file.exists():
                    state_file.unlink()
                return *get_progress(), get_jobs()
            except Exception as e:
                return f"Error: {e}", {}, []

        # Wire up events
        scan_btn.click(
            fn=scan_batch,
            inputs=[batch_size],
            outputs=[progress_text, stats_json, jobs_table],
        )

        reset_btn.click(
            fn=reset_scanner,
            outputs=[progress_text, stats_json, jobs_table],
        )

        # Load initial data
        scanner_tab.load(
            fn=lambda: (*get_progress(), get_jobs()),
            outputs=[progress_text, stats_json, jobs_table],
        )

    return scanner_tab


if __name__ == "__main__":
    # Standalone demo
    demo = create_scanner_tab()
    demo.launch()
