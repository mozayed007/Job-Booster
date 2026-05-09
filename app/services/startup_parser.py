"""Startup Parser Service - Parses startups from startups.md markdown file."""

import re
from pathlib import Path
from typing import List, Optional

from loguru import logger

from app.models.startup_model import Startup

# Category emoji mapping
CATEGORY_MAP = {
    "👁": "Computer Vision",
    "📚": "NLP",
    "🤖": "Robotics",
    "💉": "Medicine",
    "🚗": "Self-Driving Cars",
    "🗣": "Voice & Sound",
    "🧾": "Document Processing",
    "🔎": "Search & Recommendation",
    "🔬": "Science & Engineering",
    "💰": "Business",
    "👔": "Consulting",
    "🚀": "Other",
}


def _extract_link(cell: str) -> Optional[str]:
    """Extract URL from markdown link: [Link](url) or [Name](url)"""
    match = re.search(r"\[(?:Link|[^\]]+)\]\(([^)]+)\)", cell)
    return match.group(1) if match else None


def _clean_cell(cell: str) -> str:
    """Clean a table cell by removing markdown formatting."""
    # Remove markdown links, keep text
    cell = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)
    return cell.strip()


def _parse_table_row(row: str, city: str, category: str) -> Optional[Startup]:
    """Parse a single markdown table row into a Startup object."""
    # Split by pipe, remove empty first/last
    cells = [c.strip() for c in row.split("|")][1:-1]

    if len(cells) < 7:
        return None

    # Skip header rows
    if cells[0].startswith("-") or cells[0] == "Name":
        return None

    try:
        name = _clean_cell(cells[0])
        website = _extract_link(cells[1])
        linkedin = _extract_link(cells[2])
        founded = _clean_cell(cells[3]) if cells[3] != "N/A" else None

        # Employees: extract number from [N](url)
        emp_match = re.search(r"\[(\d+)\]", cells[4])
        employees = emp_match.group(1) if emp_match else None

        followers = _clean_cell(cells[5]) if cells[5] not in ("-", "N/A") else None
        funding_round = _clean_cell(cells[6]) if cells[6] not in ("-", "N/A") else None

        return Startup(
            name=name,
            city=city,
            category=category,
            website=website,
            linkedin=linkedin,
            founded=founded,
            employees=employees,
            followers=followers,
            funding_round=funding_round,
        )
    except Exception as e:
        logger.debug(f"Failed to parse row: {row[:50]}... Error: {e}")
        return None


def parse_startups_file(filepath: Optional[Path] = None) -> List[Startup]:
    """
    Parse the startups.md file and return a list of Startup objects.

    Args:
        filepath: Path to startups.md. Defaults to STARTUPS_FILE_PATH from config.

    Returns:
        List of Startup objects
    """
    if filepath is None:
        from app.core.config import settings

        filepath = Path(settings.STARTUPS_FILE_PATH)

    if not filepath.exists():
        logger.error(f"Startups file not found: {filepath}")
        return []

    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    startups: List[Startup] = []
    current_city = ""
    current_category = ""

    for line in lines:
        line = line.strip()

        # City header: ## Amsterdam
        if line.startswith("## ") and not line.startswith("### "):
            current_city = line[3:].strip()
            continue

        # Category header: ### Amsterdam - 👁 Computer Vision
        if line.startswith("### "):
            # Extract category from emoji
            for emoji, cat_name in CATEGORY_MAP.items():
                if emoji in line:
                    current_category = cat_name
                    break
            else:
                current_category = "Other"
            continue

        # Table row
        if line.startswith("|") and current_city and "|" in line[1:]:
            startup = _parse_table_row(line, current_city, current_category)
            if startup:
                startups.append(startup)

    logger.info(f"Parsed {len(startups)} startups from {filepath.name}")
    return startups


def get_startups_by_city(startups: List[Startup]) -> dict[str, List[Startup]]:
    """Group startups by city."""
    result: dict[str, List[Startup]] = {}
    for s in startups:
        result.setdefault(s.city, []).append(s)
    return result


def get_startups_by_category(startups: List[Startup]) -> dict[str, List[Startup]]:
    """Group startups by category."""
    result: dict[str, List[Startup]] = {}
    for s in startups:
        result.setdefault(s.category, []).append(s)
    return result


def filter_startups(
    startups: List[Startup],
    cities: Optional[List[str]] = None,
    categories: Optional[List[str]] = None,
    with_website_only: bool = True,
) -> List[Startup]:
    """
    Filter startups by criteria.

    Args:
        startups: List of startups to filter
        cities: Only include these cities (case-insensitive)
        categories: Only include these categories
        with_website_only: Only include startups with a website

    Returns:
        Filtered list of startups
    """
    result = startups

    if cities:
        cities_lower = [c.lower() for c in cities]
        result = [s for s in result if s.city.lower() in cities_lower]

    if categories:
        result = [s for s in result if s.category in categories]

    if with_website_only:
        result = [s for s in result if s.website]

    return result


if __name__ == "__main__":
    # Quick test
    startups = parse_startups_file()
    print(f"Total startups: {len(startups)}")

    by_city = get_startups_by_city(startups)
    print(f"Cities: {len(by_city)}")
    for city, items in sorted(by_city.items(), key=lambda x: -len(x[1]))[:5]:
        print(f"  {city}: {len(items)}")
