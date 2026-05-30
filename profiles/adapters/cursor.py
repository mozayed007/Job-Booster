"""Generate Cursor .cursor/rules/*.mdc files from agent profiles.

Usage:
    python profiles/adapters/cursor.py
    python profiles/adapters/cursor.py --output-dir .cursor/rules
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

import yaml


PROFILES_DIR = Path(__file__).parent.parent
AGENTS_DIR = PROFILES_DIR / "agents"
DEFAULT_OUTPUT = PROFILES_DIR.parent / ".cursor" / "rules"


def load_profiles() -> dict[str, Any]:
    """Load all agent profiles."""
    agents = {}
    for path in sorted(AGENTS_DIR.glob("*.yaml")):
        with open(path, encoding="utf-8") as f:
            profile = yaml.safe_load(f)
        key = profile["meta"]["name"]
        agents[key] = profile
    return agents


def generate_mdc(profile: dict[str, Any]) -> str:
    """Generate a Cursor .mdc rule file from an agent profile."""
    meta = profile["meta"]
    requirements = profile.get("requirements", {})
    io_def = profile.get("io", {})
    instructions = profile.get("instructions", "")
    adapters = profile.get("adapters", {}).get("cursor", {})

    trigger = adapters.get("trigger", f"When user asks for {meta['display_name']}")

    # Cursor .mdc format: frontmatter + markdown content
    lines = [
        "---",
        f"description: {meta['description']}",
        "---",
        "",
        f"# {meta['display_name']}",
        "",
        f"**Trigger:** {trigger}",
        "",
        instructions.strip(),
    ]

    # Add tool requirements
    tools = requirements.get("tools", [])
    if tools:
        lines.append("")
        lines.append("## Required Tools")
        lines.append("")
        for tool in tools:
            optional = " (optional)" if tool.get("optional") else ""
            lines.append(f"- `{tool['name']}`{optional}: {tool['description']}")

    # Add I/O contract
    inputs = io_def.get("inputs", [])
    outputs = io_def.get("outputs", [])
    if inputs or outputs:
        lines.append("")
        lines.append("## Interface")
        lines.append("")
        if inputs:
            lines.append("### Inputs")
            for inp in inputs:
                req = "required" if inp.get("required") else "optional"
                lines.append(f"- `{inp['name']}` ({inp['type']}, {req}): {inp['description']}")
        if outputs:
            lines.append("")
            lines.append("### Outputs")
            for out in outputs:
                lines.append(f"- `{out['name']}` ({out['type']}): {out['description']}")

    return "\n".join(lines) + "\n"


def generate_rules(output_dir: Path) -> None:
    """Generate all .mdc rule files."""
    profiles = load_profiles()
    output_dir.mkdir(parents=True, exist_ok=True)

    for name, profile in profiles.items():
        mdc_content = generate_mdc(profile)
        mdc_path = output_dir / f"{name}.mdc"
        mdc_path.write_text(mdc_content, encoding="utf-8")
        print(f"  Generated: {mdc_path}")

    print(f"\n{len(profiles)} rules written to {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Cursor rules")
    parser.add_argument(
        "--output-dir", "-o",
        type=str,
        default=str(DEFAULT_OUTPUT),
        help="Output directory for .mdc files",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    print(f"Generating Cursor rules in {output_dir}")
    generate_rules(output_dir)


if __name__ == "__main__":
    main()
