"""Prompt builders for the LangChain AI layer.

These prompts mirror the existing Pydantic AI agents so that outputs from both
stacks are comparable. They are plain text prompts; structured output is
enforced by ``with_structured_output`` on the LangChain model chain.
"""


def _truncate(text: str, limit: int) -> str:
    """Trim text to a character limit with a clear ellipsis."""
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n... [truncated]"


def build_cv_extractor_prompt(cv_text: str, job_text: str, output_format: str = "text") -> str:
    """Prompt for the CV extractor agent."""
    return f"""Extract and tailor the following CV to match the job description.

## CV
{_truncate(cv_text, 10000)}

## Job Description
{_truncate(job_text, 5000)}

## Instructions
1. Analyze the job description for key requirements and skills
2. Identify relevant experience and skills from the CV
3. Tailor the resume to emphasize matches
4. Use the XYZ formula for bullet points where possible
5. Flag any missing metrics with [placeholder]
6. Provide a relevance summary

Output format: {output_format}
"""


def build_resume_reviewer_prompt(resume_text: str, job_description: str | None = None) -> str:
    """Prompt for the resume reviewer agent."""
    parts = [
        "Review the following resume bullets and rewrite them using the XYZ formula.",
        "",
        "## Resume",
        _truncate(resume_text, 8000),
    ]

    if job_description:
        parts.extend(
            [
                "",
                "## Job Description (for context)",
                _truncate(job_description, 4000),
            ]
        )

    parts.extend(
        [
            "",
            "## Instructions",
            "1. Diagnose each bullet for issues (duty-focused, missing metrics, weak verbs, etc.)",
            "2. Rewrite using XYZ formula: Accomplished [X] as measured by [Y], by doing [Z]",
            "3. Use strong action verbs",
            "4. Flag missing metrics with [placeholder] and suggest questions",
            "5. Provide overall health score (1-10) and summary",
        ]
    )

    return "\n".join(parts)


def build_resume_tailor_prompt(resume_text: str, job_text: str, format_type: str = "text") -> str:
    """Prompt for the resume tailor agent."""
    return f"""Tailor the following resume to match the job description.

## Resume
{_truncate(resume_text, 6000)}

## Job Description
{_truncate(job_text, 4000)}

## Instructions
1. Identify key requirements and skills from the job description
2. Reorder and emphasize relevant experience
3. Enhance bullet points using the XYZ formula where possible
4. Add relevant keywords naturally
5. Maintain truthfulness — do not fabricate experience

Output format: {format_type}
"""


def build_cover_letter_prompt(
    resume_text: str,
    job_text: str,
    company_name: str | None = None,
    hiring_manager: str | None = None,
) -> str:
    """Prompt for the cover letter generator agent."""
    parts = [
        "Generate a tailored cover letter based on the following resume and job description.",
        "",
        "## Resume",
        _truncate(resume_text, 6000),
        "",
        "## Job Description",
        _truncate(job_text, 4000),
    ]

    if company_name:
        parts.append(f"\nCompany: {company_name}")
    if hiring_manager:
        parts.append(f"Hiring Manager: {hiring_manager}")

    return "\n".join(parts)


def build_job_finder_prompt(
    resume_text: str,
    top_skills: list[str] | None = None,
    target_roles: list[str] | None = None,
    location_preference: str = "remote",
    seniority_level: str | None = None,
    visa_required: bool = False,
    max_results: int = 15,
) -> str:
    """Prompt for the job finder agent."""
    parts = [
        "Find AI/ML job listings matching the following profile.",
        "",
        "## Resume",
        _truncate(resume_text, 5000),
        "",
        "## Search Criteria",
        f"- Location: {location_preference}",
    ]

    if top_skills:
        parts.append(f"- Top Skills: {', '.join(top_skills)}")
    if target_roles:
        parts.append(f"- Target Roles: {', '.join(target_roles)}")
    if seniority_level:
        parts.append(f"- Seniority: {seniority_level}")
    if visa_required:
        parts.append("- Visa Sponsorship: Required")

    parts.extend(
        [
            f"- Max Results: {max_results}",
            "",
            "## Instructions",
            "1. Generate targeted search queries for credible sources",
            "2. Score each listing on skill overlap, role match, location fit",
            "3. Research visa sponsorship status where relevant",
            "4. Provide a summary with recommendations",
        ]
    )

    return "\n".join(parts)


def build_onboarding_chat_prompt(transcript: str, user_msg: str) -> str:
    """Prompt for a single onboarding chat turn (free-text response)."""
    parts = ["CHAT: You are mid-conversation with the user."]
    if transcript:
        parts.extend(["", "Conversation so far:", transcript])
    parts.extend(
        [
            "",
            f"User's latest message: {user_msg}",
            "",
            "Respond with your next question (1-3 sentences), or emit "
            "[PROFILE_READY] on its own line if you have enough across at "
            "least 3 of the 5 areas (hobbies, interests, free-time, favorite "
            "tech/domains, work style).",
        ]
    )
    return "\n".join(parts)


def build_onboarding_finalize_prompt(history: list[dict]) -> str:
    """Prompt to finalize an onboarding conversation into a structured profile."""
    lines: list[str] = []
    for turn in history:
        role = turn.get("role", "user")
        content = turn.get("content", "")
        label = "User" if role == "user" else "Assistant"
        lines.append(f"{label}: {content}")
    transcript = "\n".join(lines)
    return (
        f"FINALIZE: Convert this onboarding conversation into a structured profile.\n\n{transcript}"
    )


def build_gap_recommendation_prompt(
    gaps: list[str],
    personal_context: dict | None = None,
    job_context: str = "",
) -> str:
    """Prompt for the gap-recommendation agent."""
    import json

    parts = [
        "Generate enjoyable, personalized recommendations that cover the "
        "following technical skill gaps.",
        "",
        "## Skill Gaps",
    ]
    for gap in gaps:
        parts.append(f"- {gap}")

    parts.extend(["", "## Personal Context"])
    if personal_context and any(personal_context.values()):
        parts.append("```json")
        parts.append(json.dumps(personal_context, indent=2, default=str))
        parts.append("```")
    else:
        parts.append(
            "(No personal context provided — user has not completed onboarding. "
            "Produce broadly engaging recs and note the profile was empty.)"
        )

    if job_context:
        parts.extend(["", f"## Job Context\n{job_context}"])

    parts.extend(
        [
            "",
            f"Provide 1-3 recommendations per gap (fewer per gap when there are "
            f"many gaps — scale by gap count). Map each rec to a specific hobby or "
            f"interest from the personal context. Total gaps: {len(gaps)}.",
        ]
    )
    return "\n".join(parts)
