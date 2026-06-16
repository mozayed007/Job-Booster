"""Gradio Account tab — login, profile editor, API token."""

import gradio as gr

from app.ui.api_client import (
    auth_login,
    auth_register,
    settings_get_profile,
    settings_put_profile,
)
from app.ui.helpers import run_async


def _comma_list(text: str) -> list[str]:
    return [x.strip() for x in (text or "").split(",") if x.strip()]


def _join_list(items: list) -> str:
    if not items:
        return ""
    return ", ".join(str(x) for x in items)


def build_auth_tab(api_token) -> None:
    gr.Markdown(
        "### Account\n"
        "Sign in for protected routes. Edit your job-search profile "
        "(saved to `data/user_profile.yaml`)."
    )

    with gr.Tabs():
        with gr.Tab("Sign in"):
            with gr.Row():
                with gr.Column():
                    auth_email = gr.Textbox(label="Email", placeholder="you@example.com")
                    auth_password = gr.Textbox(label="Password", type="password")
                    auth_name = gr.Textbox(label="Name (register only)")
                    with gr.Row():
                        register_btn = gr.Button("Register")
                        login_btn = gr.Button("Sign in", variant="primary")
                    auth_result = gr.JSON(label="Auth response")
                    token_display = gr.Markdown("**Token:** _(not signed in)_")
                    token_copy = gr.Textbox(label="Active token", lines=2)
                    save_token_btn = gr.Button("Use pasted token", size="sm")

        with gr.Tab("Profile"):
            profile_load_btn = gr.Button("Load profile", variant="primary")
            prof_skills = gr.Textbox(label="Skills (comma-separated)", lines=2)
            prof_locations = gr.Textbox(label="Preferred locations", lines=2)
            prof_categories = gr.Textbox(label="Preferred categories / industries", lines=2)
            prof_roles = gr.Textbox(label="Target role keywords", lines=2)
            prof_visa = gr.Checkbox(label="Visa sponsorship required")
            prof_bigset_enabled = gr.Checkbox(label="BigSet import enabled", value=True)
            prof_prefer_imported = gr.Checkbox(
                label="Prefer imported corpus over web search",
                value=True,
            )
            prof_min_fit = gr.Slider(0, 1, value=0.25, step=0.05, label="Min fit score")
            prof_default_mapping = gr.Textbox(
                label="Default mapping id",
                value="generic_job_listing",
            )
            profile_save_btn = gr.Button("Save profile", variant="primary")
            profile_save_result = gr.JSON(label="Save result")

    def _token_md(token: str) -> str:
        if not token or not str(token).strip():
            return "**Token:** _(not signed in)_"
        t = str(token).strip()
        preview = t[:24] + "…" if len(t) > 28 else t
        return f"**Token:** `{preview}` ({len(t)} chars)"

    def register(email, password, name):
        if not email or not password:
            return {"Error": "Email and password required"}, _token_md(""), ""
        try:
            result = run_async(auth_register(email, password, name or ""))
            if isinstance(result, dict) and "Error" not in result:
                token = result.get("token", "")
            else:
                token = ""
            return result, _token_md(token), token
        except Exception as e:
            return {"Error": str(e)}, _token_md(""), ""

    def login(email, password):
        if not email or not password:
            return {"Error": "Email and password required"}, _token_md(""), ""
        try:
            result = run_async(auth_login(email, password))
            if isinstance(result, dict) and result.get("Error"):
                return result, _token_md(""), ""
            token = result.get("token", "") if isinstance(result, dict) else ""
            return result, _token_md(token), token
        except Exception as e:
            return {"Error": str(e)}, _token_md(""), ""

    def use_pasted_token(pasted):
        token = (pasted or "").strip()
        return _token_md(token), token

    def load_profile_fields(token):
        if not token:
            return (
                "",
                "",
                "",
                "",
                False,
                True,
                True,
                0.25,
                "generic_job_listing",
                {"Error": "Sign in first"},
            )
        try:
            data = run_async(settings_get_profile(token))
            if data.get("Error"):
                return (
                    "",
                    "",
                    "",
                    "",
                    False,
                    True,
                    True,
                    0.25,
                    "generic_job_listing",
                    data,
                )
            p = data.get("profile", data)
            bs = p.get("bigset", {}) or {}
            return (
                _join_list(p.get("skills", [])),
                _join_list(p.get("preferred_locations", [])),
                _join_list(p.get("preferred_categories", [])),
                _join_list(p.get("target_role_keywords", [])),
                bool(p.get("visa_support_required", False)),
                bool(bs.get("enabled", True)),
                bool(bs.get("prefer_imported_jobs", True)),
                float(bs.get("min_fit_score", 0.25)),
                str(bs.get("default_mapping", "generic_job_listing")),
                {"success": True},
            )
        except Exception as e:
            return (
                "",
                "",
                "",
                "",
                False,
                True,
                True,
                0.25,
                "generic_job_listing",
                {"Error": str(e)},
            )

    def save_profile_fields(
        token,
        skills,
        locs,
        cats,
        roles,
        visa,
        bs_en,
        prefer_imported,
        min_fit,
        mapping,
    ):
        if not token:
            return {"Error": "Sign in first"}
        profile = {
            "skills": _comma_list(skills),
            "preferred_locations": _comma_list(locs),
            "preferred_categories": _comma_list(cats),
            "target_role_keywords": _comma_list(roles),
            "visa_support_required": bool(visa),
            "bigset": {
                "enabled": bool(bs_en),
                "prefer_imported_jobs": bool(prefer_imported),
                "min_fit_score": float(min_fit),
                "default_mapping": (mapping or "generic_job_listing").strip(),
            },
        }
        try:
            return run_async(settings_put_profile(token, profile))
        except Exception as e:
            return {"Error": str(e)}

    register_btn.click(
        fn=register,
        inputs=[auth_email, auth_password, auth_name],
        outputs=[auth_result, token_display, api_token],
    )
    login_btn.click(
        fn=login,
        inputs=[auth_email, auth_password],
        outputs=[auth_result, token_display, api_token],
    )
    save_token_btn.click(
        fn=use_pasted_token,
        inputs=[token_copy],
        outputs=[token_display, api_token],
    )
    token_copy.change(fn=use_pasted_token, inputs=[token_copy], outputs=[token_display, api_token])

    profile_load_btn.click(
        fn=load_profile_fields,
        inputs=[api_token],
        outputs=[
            prof_skills,
            prof_locations,
            prof_categories,
            prof_roles,
            prof_visa,
            prof_bigset_enabled,
            prof_prefer_imported,
            prof_min_fit,
            prof_default_mapping,
            profile_save_result,
        ],
    )
    profile_save_btn.click(
        fn=save_profile_fields,
        inputs=[
            api_token,
            prof_skills,
            prof_locations,
            prof_categories,
            prof_roles,
            prof_visa,
            prof_bigset_enabled,
            prof_prefer_imported,
            prof_min_fit,
            prof_default_mapping,
        ],
        outputs=[profile_save_result],
    )
