"""Web search and fetch tools for Pydantic AI agents.

Uses TinyFish SDK for web search/fetch and wraps functions as Pydantic AI Tool objects.
Import search_tool / fetch_tool and set as class attribute on any agent that needs them.
"""

import os
from functools import lru_cache

from loguru import logger
from pydantic_ai import Tool


class _TinyFishAPIError(Exception):
    """Fallback exception class when the TinyFish SDK is not installed."""


try:
    from tinyfish import APIError, AsyncTinyFish
except ImportError:
    APIError = _TinyFishAPIError  # type: ignore[misc,assignment]
    AsyncTinyFish = None  # type: ignore[misc,assignment]


@lru_cache(maxsize=1)
def _get_client() -> "AsyncTinyFish":
    if AsyncTinyFish is None:
        raise RuntimeError("tinyfish is not installed")
    api_key = os.getenv("TINYFISH_API_KEY")
    if not api_key:
        raise ValueError("TINYFISH_API_KEY environment variable not set")
    return AsyncTinyFish(api_key=api_key)


async def web_search(query: str, max_results: int = 5) -> str:
    """Search the web for current information and return formatted results.

    Each result includes title, URL, and a snippet. Use this to find real job
    listings, company or hiring-manager details, tech stack info, and news.

    Args:
        query: The search query string
        max_results: Number of results to return (1-10, default 5)
    """
    try:
        client = _get_client()
        resp = await client.search.query(query=query)
        results = resp.results[:max_results]

        if not results:
            return "No search results found."

        lines = []
        for i, r in enumerate(results, 1):
            lines.append(f"{i}. {r.title}")
            lines.append(f"   URL: {r.url}")
            lines.append(f"   {r.snippet}")
            lines.append("")

        return "\n".join(lines)
    except APIError as e:
        logger.error(f"Web search failed: {e}")
        return f"Error searching the web: {e}"


async def web_fetch(url: str) -> str:
    """Fetch and extract readable content from a URL.

    Returns the page title, description, and body text in markdown format.
    Use this to read a specific job posting, company about page, engineering
    blog post, or LinkedIn profile.

    Args:
        url: Full URL to fetch including protocol (e.g., https://example.com/careers)
    """
    try:
        client = _get_client()
        resp = await client.fetch.get_contents(urls=[url], format="markdown")

        if resp.errors:
            error_msg = "; ".join(str(e) for e in resp.errors)
            return f"Error fetching URL: {error_msg}"

        if not resp.results:
            return "No content retrieved from the URL."

        result = resp.results[0]
        parts = []
        if result.title:
            parts.append(f"# {result.title}")
            parts.append("")
        if result.description:
            parts.append(f"_{result.description}_")
            parts.append("")
        if result.text:
            parts.append(result.text)

        return "\n".join(parts) if parts else "No content retrieved."
    except APIError as e:
        logger.error(f"Web fetch failed for {url}: {e}")
        return f"Error fetching URL: {e}"


search_tool = Tool(
    web_search,
    takes_ctx=False,
    description=(
        "Search the web for current information. Each result includes title, URL, and snippet."
    ),
)

fetch_tool = Tool(
    web_fetch,
    takes_ctx=False,
    description=(
        "Fetch and extract readable content from a URL. "
        "Returns page title, description, and body text in markdown format."
    ),
)
