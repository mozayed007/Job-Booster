"""LaTeX template engine for rendering structured Resume data into .tex files."""

import re
from datetime import date
from pathlib import Path

from loguru import logger


def _get_template_path() -> Path:
    from app.core.config import settings

    return Path(settings.RESUME_TEMPLATE_PATH)


def _get_output_dir() -> Path:
    from app.core.config import settings

    return Path(settings.RESUME_OUTPUT_DIR)


def _format_date(d: date | None) -> str:
    if not d:
        return "Present"
    return d.strftime("%b %Y")


def _escape_latex(text: str) -> str:
    """Escape special LaTeX characters."""
    if not text:
        return ""
    # Order matters: backslash first
    text = text.replace("\\", "\\textbackslash{}")
    for char in ["&", "%", "$", "#", "_"]:
        text = text.replace(char, f"\\{char}")
    text = text.replace("~", "\\textasciitilde{}")
    text = text.replace("^", "\\textasciicircum{}")
    return text


def _build_contact_header(contact) -> str:
    """Build the centered contact header."""
    parts = []
    if contact.phone:
        parts.append(_escape_latex(contact.phone))
    if contact.email:
        parts.append(_escape_latex(contact.email))
    if contact.linkedin:
        parts.append(_escape_latex(contact.linkedin))
    if contact.github:
        parts.append(_escape_latex(contact.github))
    if contact.website:
        parts.append(_escape_latex(contact.website))
    if contact.location:
        parts.append(_escape_latex(contact.location))

    separator = " \\quad | \\quad "
    contact_line = separator.join(parts)

    name = _escape_latex(contact.name or "Your Name")
    return f"""\\begin{{center}}
    \\textbf{{\\Large {name}}} \\\\
    \\vspace{{3pt}}
    \\small{{{contact_line}}}
\\end{{center}}"""


def _build_summary(summary: str | None) -> str:
    if not summary:
        return ""
    return f"\\section{{Professional Summary}}\n{_escape_latex(summary)}"


def _build_experience(work_experience) -> str:
    if not work_experience:
        return ""

    lines = ["\\section{Experience}", "", "\\begin{itemize}[label={}, leftmargin=0in]", ""]

    for exp in work_experience:
        company = _escape_latex(exp.company)
        title = _escape_latex(exp.position)
        dates = f"{_format_date(exp.start_date)} -- {_format_date(exp.end_date)}"
        location = _escape_latex(exp.location or "")

        lines.append(f"    \\resumeSubheading{{{company}}}{{{dates}}}{{{title}}}{{{location}}}")
        lines.append("    \\begin{itemize}[label={--}]")

        if exp.description:
            lines.append(f"      \\resumeItem{{{_escape_latex(exp.description)}}}")
        for ach in exp.achievements:
            lines.append(f"      \\resumeItem{{{_escape_latex(ach)}}}")

        lines.append("    \\end{itemize}")
        lines.append("")

    lines.append("\\end{itemize}")
    return "\n".join(lines)


def _build_projects(projects) -> str:
    if not projects:
        return ""

    lines = ["\\section{Projects}", "", "\\begin{itemize}[label={}, leftmargin=0in]", ""]

    for proj in projects:
        name = _escape_latex(proj.name)
        tech = ", ".join(proj.technologies) if proj.technologies else ""
        heading = f"{name} -- {_escape_latex(tech)}" if tech else name
        date_str = ""

        lines.append(f" \\resumeProjectHeading{{{heading}}}{{{date_str}}}")
        lines.append(" \\begin{itemize}[label={--}]")

        if proj.description:
            lines.append(f"    \\resumeItem{{{_escape_latex(proj.description)}}}")

        lines.append(" \\end{itemize}")
        lines.append("")

    lines.append("\\end{itemize}")
    return "\n".join(lines)


def _build_skills(skills) -> str:
    if not skills:
        return ""

    # Group by category
    categories: dict[str, list[str]] = {}
    for skill in skills:
        cat = skill.category or "Skills"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(skill.name)

    lines = ["\\section{Skills}", "", "\\begin{itemize}[label={}, leftmargin=0in]"]
    for cat, names in categories.items():
        joined = ", ".join(names)
        lines.append(f"    \\item \\textbf{{{_escape_latex(cat)}}}: {_escape_latex(joined)}")
    lines.append("\\end{itemize}")

    return "\n".join(lines)


def _build_education(education) -> str:
    if not education:
        return ""

    lines = ["\\section{Education}", "", "\\begin{itemize}[label={}, leftmargin=0in]"]

    for edu in education:
        inst = _escape_latex(edu.institution)
        dates = _format_date(edu.start_date)
        degree = f"{edu.degree}, {edu.field_of_study}"
        location = ""

        lines.append(
            f"    \\resumeSubheading{{{inst}}}{{{dates}}}{{{_escape_latex(degree)}}}{{{location}}}"
        )

        if edu.gpa:
            lines.append("    \\begin{itemize}[label={--}]")
            lines.append(f"      \\resumeItem{{\\textbf{{GPA}}: {edu.gpa}}}")
            lines.append("    \\end{itemize}")

    lines.append("\\end{itemize}")
    return "\n".join(lines)


def render_resume(resume, template_path: Path | None = None) -> str:
    """Render a Resume model into a complete LaTeX document using the template.

    Args:
        resume: Resume Pydantic model with all structured data.
        template_path: Path to the .tex template. Defaults to data/templates/resume_template.tex.

    Returns:
        Complete LaTeX source string ready for compilation.
    """
    tpl_path = template_path or _get_template_path()

    if not tpl_path.exists():
        logger.warning(f"Template not found at {tpl_path}, using fallback")
        return _render_fallback(resume)

    template = tpl_path.read_text(encoding="utf-8")

    # Extract preamble: everything up to and including \begin{document}
    preamble_match = re.search(r"(.*?\\begin\{document\})", template, re.DOTALL)
    if not preamble_match:
        logger.error("Could not find \\begin{document} in template")
        return _render_fallback(resume)

    preamble = preamble_match.group(1)

    # Build body sections
    sections = [
        _build_contact_header(resume.contact_info),
        _build_summary(resume.summary),
        _build_experience(resume.work_experience),
        _build_projects(resume.projects),
        _build_skills(resume.skills),
        _build_education(resume.education),
    ]

    body = "\n\n".join(s for s in sections if s)

    return f"{preamble}\n\n{body}\n\n\\end{{document}}\n"


def _render_fallback(resume) -> str:
    """Fallback renderer if template file is missing."""
    lines = [
        r"\documentclass[10pt, letterpaper]{extarticle}",
        r"\usepackage[left=0.55in, right=0.55in, top=0.45in, bottom=0.45in]{geometry}",
        r"\usepackage{enumitem}",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage{titlesec}",
        r"\usepackage{tabularx}",
        r"",
        r"\newcommand{\resumeItem}[1]{\item{#1}}",
        r"\newcommand{\resumeSubheading}[4]{",
        r"  \item",
        r"    \begin{tabular*}{1.0\textwidth}[t]{l@{\extracolsep{\fill}}r}",
        r"      \textbf{#1} & \textit{#4} \\",
        r"      \textit{#3} & #2 \\",
        r"    \end{tabular*}\vspace{1.5pt}",
        r"}",
        r"\newcommand{\resumeProjectHeading}[2]{",
        r"    \item",
        r"    \begin{tabular*}{\textwidth}[t]{@{}p{0.82\textwidth}@{\extracolsep{\fill}}r@{}}",
        r"       \textbf{#1} & \textit{#2} \\",
        r"    \end{tabular*}\vspace{2pt}",
        r"}",
        r"",
        r"\begin{document}",
        "",
    ]
    body = "\n\n".join(
        s
        for s in [
            _build_contact_header(resume.contact_info),
            _build_summary(resume.summary),
            _build_experience(resume.work_experience),
            _build_projects(resume.projects),
            _build_skills(resume.skills),
            _build_education(resume.education),
        ]
        if s
    )
    lines.append(body)
    lines.append(r"\end{document}")
    return "\n".join(lines)


def get_output_path(job_title: str, company: str = "", extension: str = "tex") -> Path:
    """Generate an output file path for a tailored resume.

    Creates data/resumes/output/<company>_<job_title>.tex
    """
    output_dir = _get_output_dir()
    output_dir.mkdir(parents=True, exist_ok=True)

    # Sanitize filename
    safe_parts = []
    if company:
        safe_parts.append(re.sub(r"[^\w\s-]", "", company).strip().replace(" ", "_"))
    if job_title:
        safe_parts.append(re.sub(r"[^\w\s-]", "", job_title).strip().replace(" ", "_"))

    filename = "_".join(safe_parts) if safe_parts else "tailored_resume"
    return output_dir / f"{filename}.{extension}"
