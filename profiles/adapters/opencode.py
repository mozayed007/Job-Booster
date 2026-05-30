"""Generate opencode SKILL.md files from agent profiles.

Usage:
    python profiles/adapters/opencode.py
    python profiles/adapters/opencode.py --output-dir .opencode/skills
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml


PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"
DEFAULT_OUTPUT = PROFILES_DIR.parent / ".opencode" / "skills"


def load_profiles() -> dict[str, Any]:
    """Load all agent profiles."""
    agents = {}
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        key = profile["meta"]["name"]
        agents[key] = profile
    return agents


def generate_skill_md(profile: dict[str, Any]) -> str:
    """Generate a SKILL.md file from an agent profile."""
    meta = profile["meta"]
    requirements = profile.get("requirements", {})
    io_def = profile.get("io", {})
    instructions = profile.get("instructions", "")

    # Build frontmatter
    frontmatter = {
        "name": meta["name"],
        "description": meta["description"],
    }

    # Build skill content
    lines = [
        "---",
        yaml.dump(frontmatter, default_flow_style=True, allow_unicode=True).strip(),
        "---",
        "",
        instructions.strip(),
    ]

    # Add tool requirements as context
    tools = requirements.get("tools", [])
    if tools:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Required Tools")
        lines.append("")
        for tool in tools:
            optional = " (optional)" if tool.get("optional") else ""
            lines.append(f"- **{tool['name']}**{optional}: {tool['description']}")
            if tool.get("fallback"):
                lines.append(f"  - Fallback: {tool['fallback']}")

    # Add I/O contract
    inputs = io_def.get("inputs", [])
    outputs = io_def.get("outputs", [])
    if inputs or outputs:
        lines.append("")
        lines.append("---")
        lines.append("")
        lines.append("## Interface")
        lines.append("")
        if inputs:
            lines.append("### Inputs")
            lines.append("")
            lines.append("| Name | Type | Required | Description |")
            lines.append("|------|------|----------|-------------|")
            for inp in inputs:
                req = "Yes" if inp.get("required") else "No"
                lines.append(f"| {inp['name']} | {inp['type']} | {req} | {inp['description']} |")
        if outputs:
            lines.append("")
            lines.append("### Outputs")
            lines.append("")
            for out in outputs:
                lines.append(f"- **{out['name']}** ({out['type']}): {out['description']}")

    return "\n".join(lines) + "\n"


def generate_skills(output_dir: Path) -> None:
    """Generate all SKILL.md files."""
    profiles = load_profiles()
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, profile in profiles.items():
        skill_dir = output_dir / name
        skill_dir.mkdir(parents=True, exist_ok=True)

        skill_content = generate_skill_md(profile)
        skill_path = skill_dir / "SKILL.md"
        skill_path.write_text(skill_content, encoding="utf-8")
        print(f"  Generated: {skill_path}")

    print(f"\n{len(profiles)} skills written to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate opencode skills")
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output directory for SKILL.md files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    print(f"Generating opencode skills in {output_dir}")
    generate_skills(output_dir)


if __name__ == "__main__":
    main()
