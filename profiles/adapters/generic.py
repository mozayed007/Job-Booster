"""Generate a standalone prompt pack from agent profiles.

Produces a directory of self-contained markdown files — one per agent —
that can be pasted into any LLM chat or loaded by any agentic tool.

Usage:
    python profiles/adapters/generic.py
    python profiles/adapters/generic.py --output-dir ./prompt-pack
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml

PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"
DEFAULT_OUTPUT = PROFILES_DIR / "prompt-pack"


def load_profiles() -> dict[str, Any]:
    """Load all agent profiles."""
    agents = {}
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        key = profile["meta"]["name"]
        agents[key] = profile
    return agents


def generate_prompt_markdown(profile: dict[str, Any]) -> str:
    """Generate a self-contained prompt markdown file."""
    meta = profile["meta"]
    requirements = profile.get("requirements", {})
    io_def = profile.get("io", {})
    instructions = profile.get("instructions", "")
    specialization = profile.get("specialization", {})

    lines = [
        f"# {meta['display_name']}",
        "",
        f"> {meta['description']}",
        "",
        f"**Version:** {meta['version']}  ",
        f"**Author:** {meta['author']}  ",
        f"**Tags:** {', '.join(meta.get('tags', []))}",
        "",
    ]

    # Specialization note
    field = specialization.get("field", "")
    if field:
        lines.append(f"**Specialized for:** {field}")
        lines.append("")

    # LLM requirements
    llm = requirements.get("llm", {})
    if llm:
        lines.append("## LLM Requirements")
        lines.append("")
        lines.append(f"- **Minimum capability:** {llm.get('min_capability', 'text')}")
        lines.append(f"- **Context window:** {llm.get('context_window', 8000)} tokens")
        if llm.get("preferred_models"):
            lines.append(f"- **Preferred models:** {', '.join(llm['preferred_models'])}")
        lines.append("")

    # Tool requirements
    tools = requirements.get("tools", [])
    if tools:
        lines.append("## Required Tools")
        lines.append("")
        for tool in tools:
            optional = " (optional)" if tool.get("optional") else ""
            lines.append(f"- **{tool['name']}**{optional}: {tool['description']}")
            if tool.get("fallback"):
                lines.append(f"  - Fallback: {tool['fallback']}")
        lines.append("")

    # Instructions
    lines.append("---")
    lines.append("")
    lines.append(instructions.strip())

    # I/O contract
    inputs = io_def.get("inputs", [])
    outputs = io_def.get("outputs", [])
    if inputs or outputs:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Interface Contract")
        lines.append("")
        if inputs:
            lines.append("### Inputs")
            lines.append("")
            lines.append("| Name | Type | Required | Default | Description |")
            lines.append("|------|------|----------|---------|-------------|")
            for inp in inputs:
                req = "Yes" if inp.get("required") else "No"
                default = inp.get("default", "")
                lines.append(
                    f"| {inp['name']} | {inp['type']} | {req} | {default} | {inp['description']} |"
                )
        if outputs:
            lines.append("")
            lines.append("### Outputs")
            lines.append("")
            lines.append("| Name | Type | Description |")
            lines.append("|------|------|-------------|")
            for out in outputs:
                lines.append(f"| {out['name']} | {out['type']} | {out['description']} |")

    return "\n".join(lines) + "\n"


def generate_pack(output_dir: Path) -> None:
    """Generate all prompt files."""
    profiles = load_profiles()
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, profile in profiles.items():
        content = generate_prompt_markdown(profile)
        md_path = output_dir / f"{name}.md"
        md_path.write_text(content, encoding="utf-8")
        print(f"  Generated: {md_path}")

    # Generate an index
    index_lines = [
        "# Agent Prompt Pack",
        "",
        f"{len(profiles)} agents ready to use.",
        "",
        "| Agent | Description |",
        "|-------|-------------|",
    ]
    for name, profile in profiles.items():
        desc = profile["meta"]["description"][:80]
        index_lines.append(f"| [{profile['meta']['display_name']}]({name}.md) | {desc} |")

    index_path = output_dir / "INDEX.md"
    index_path.write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(f"  Generated: {index_path}")

    print(f"\n{len(profiles)} prompts written to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate generic prompt pack")
    parser.add_argument(
        "--output-dir",
        "-o",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output directory for prompt files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    print(f"Generating prompt pack in {output_dir}")
    generate_pack(output_dir)


if __name__ == "__main__":
    main()
