"""Gradio Onboarding tab — conversational personal context profiler.

This tab runs a short chat interview to gather the user's hobbies, interests,
and work style. The result is saved to the user's profile_json and is consumed
ONLY by the gap-recommendation agent — never by resume/cover-letter agents.
"""

import gradio as gr

from app.ui.api_client import (
    onboarding_chat,
    onboarding_finalize,
    onboarding_get_profile,
)
from app.ui.helpers import run_async


def _history_to_gradio(history: list[dict]) -> list[dict]:
    """Convert API history format [{role, content}] to Gradio chatbot format."""
    return [
        {"role": turn.get("role", "user"), "content": turn.get("content", "")}
        for turn in (history or [])
    ]


def _gradio_to_history(messages: list[dict]) -> list[dict]:
    """Convert Gradio chatbot messages to API history format."""
    return [
        {"role": msg.get("role", "user"), "content": msg.get("content", "")}
        for msg in (messages or [])
    ]


def _format_profile_preview(context: dict | None) -> str:
    """Render a saved personal context as a readable markdown summary."""
    if not context:
        return "_(No personal context saved yet. Run the chat interview above.)_"

    lines = ["### Saved Personal Context", ""]
    fields = [
        ("Hobbies", "hobbies"),
        ("Interests", "interests"),
        ("Free-time activities", "free_time_activities"),
        ("Favorite tech / domains", "favorite_tech_or_domains"),
        ("Work style", "work_style"),
        ("Short bio", "short_bio"),
    ]
    for label, key in fields:
        val = context.get(key)
        if not val:
            continue
        if isinstance(val, list):
            val = ", ".join(str(v) for v in val)
        lines.append(f"**{label}:** {val}")
    lines.append("")
    lines.append(
        "_This context is used ONLY by the gap-recommendation agent. "
        "Resume and cover-letter agents never read it._"
    )
    return "\n".join(lines)


def build_onboarding_tab(api_token):
    """Build the Onboarding tab.

    Returns nothing — components are created in the current Blocks context.
    ``api_token`` is a gr.State<string> holding the JWT for authed calls.
    """

    gr.Markdown(
        "### Onboarding\n"
        "A short, friendly chat to learn what you enjoy outside of work — your "
        "hobbies, interests, and work style. Later, when technical skill gaps "
        "appear, the recommendations agent will suggest projects you'll "
        "actually enjoy.\n\n"
        "**This data never touches your resume** — it only helps recommend "
        "enjoyable ways to fill skill gaps."
    )

    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(
                label="Onboarding chat",
                height=400,
                placeholder=(
                    "Click 'Start chat' to begin. The agent will ask a few "
                    "quick questions about your hobbies and interests."
                ),
            )
            with gr.Row():
                chat_input = gr.Textbox(
                    label="Your message",
                    placeholder="Type your answer and press Enter…",
                    scale=4,
                    interactive=False,
                )
                send_btn = gr.Button("Send", variant="primary", scale=1, interactive=False)

            with gr.Row():
                start_btn = gr.Button("Start chat", variant="primary")
                save_btn = gr.Button("Save profile", variant="stop", interactive=False)
                load_btn = gr.Button("Load saved profile")

            profile_status = gr.Markdown("")

        with gr.Column(scale=2):
            gr.Markdown("### Your Profile")
            profile_preview = gr.Markdown(
                "_(No personal context saved yet. Run the chat interview above.)_"
            )
            profile_json_out = gr.JSON(label="Raw profile JSON", visible=False)

    # Hidden state to track the conversation history in API format.
    api_history = gr.State(value=[])

    # --- Start chat --------------------------------------------------------
    def start_chat(token):
        """Kick off the interview by sending a greeting."""
        if not token or not token.strip():
            return (
                [{"role": "assistant", "content": "Please sign in first (Account tab)."}],
                [],
                "⚠️ Sign in first from the Account tab, then come back here.",
                gr.Button(interactive=False),
                gr.Button(interactive=True),
                gr.Textbox(interactive=False),
            )
        result = run_async(onboarding_chat(token, "Hi, I'd like to get started.", []))
        if "Error" in result:
            reply = result["Error"]
            return (
                [{"role": "assistant", "content": reply}],
                [],
                reply,
                gr.Button(interactive=False),
                gr.Button(interactive=True),
                gr.Textbox(interactive=False),
            )

        reply = result.get("reply", "Hi! Let's get started.")
        history = result.get("history", [])
        ready = result.get("profile_ready", False)
        if ready:
            status = "✅ Enough context gathered! Click **Save profile** to finalize."
        else:
            status = "💬 Answer the question, or click **Save profile** when you're done."
        return (
            [{"role": "assistant", "content": reply}],
            history,
            status,
            gr.Button(interactive=False),
            gr.Button(interactive=True),
            gr.Textbox(interactive=True),
        )

    start_btn.click(
        fn=start_chat,
        inputs=[api_token],
        outputs=[chatbot, api_history, profile_status, start_btn, send_btn, chat_input],
    )

    # --- Send message ------------------------------------------------------
    def send_message(token, message, history_api, chatbot_msgs):
        """Send a user message and get the agent's reply."""
        if not message.strip():
            return chatbot_msgs, history_api, "", gr.Button(interactive=True), ""
        result = run_async(onboarding_chat(token, message, history_api))
        if "Error" in result:
            reply = result["Error"]
            new_msgs = chatbot_msgs + [
                {"role": "user", "content": message},
                {"role": "assistant", "content": reply},
            ]
            return new_msgs, history_api, "", gr.Button(interactive=True), ""

        reply = result.get("reply", "")
        new_history = result.get("history", history_api)
        ready = result.get("profile_ready", False)
        new_msgs = chatbot_msgs + [
            {"role": "user", "content": message},
            {"role": "assistant", "content": reply},
        ]
        if ready:
            status = "✅ Enough context gathered! Click **Save profile** to finalize."
        else:
            status = "💬 Continue the conversation, or click **Save profile** when ready."
        return new_msgs, new_history, status, gr.Button(interactive=True), ""

    send_btn.click(
        fn=send_message,
        inputs=[api_token, chat_input, api_history, chatbot],
        outputs=[chatbot, api_history, profile_status, send_btn, chat_input],
    )
    chat_input.submit(
        fn=send_message,
        inputs=[api_token, chat_input, api_history, chatbot],
        outputs=[chatbot, api_history, profile_status, send_btn, chat_input],
    )

    # --- Save / finalize ---------------------------------------------------
    def save_profile(token, history_api):
        if not history_api:
            return "⚠️ No conversation to save. Start the chat first.", ""
        result = run_async(onboarding_finalize(token, history_api))
        if "Error" in result:
            return f"❌ {result['Error']}", ""
        context = result.get("personal_context", {})
        return (
            "✅ Profile saved! Your personal context is ready for the gap-recommendation agent.",
            _format_profile_preview(context),
        )

    save_btn.click(
        fn=save_profile,
        inputs=[api_token, api_history],
        outputs=[profile_status, profile_preview],
    )

    # --- Load saved profile ------------------------------------------------
    def load_profile(token):
        result = run_async(onboarding_get_profile(token))
        if "Error" in result:
            return f"❌ {result['Error']}", "", None
        context = result.get("personal_context")
        return _format_profile_preview(context), context, context

    load_btn.click(
        fn=load_profile,
        inputs=[api_token],
        outputs=[profile_preview, profile_json_out, profile_json_out],
    )
