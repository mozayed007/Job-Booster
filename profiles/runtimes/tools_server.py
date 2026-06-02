"""REST Tools Server — serves agent tools as HTTP endpoints.

Exposes the tools from profiles/tools/openapi_tools.yaml as a running
REST server. Any platform can call these endpoints.

Usage:
    python profiles/runtimes/tools_server.py
    python profiles/runtimes/tools_server.py --port 8052
"""

from __future__ import annotations

import asyncio
import os
import sys
from typing import Any

import httpx

# ──────────────────────────────────────────────
# Tool implementations
# ──────────────────────────────────────────────


async def web_search_impl(query: str, max_results: int = 5) -> dict[str, Any]:
    """Search the web using available backend."""
    # Try TinyFish first
    api_key = os.getenv("TINYFISH_API_KEY")
    if api_key:
        try:
            return await _tinyfish_search(query, max_results, api_key)
        except Exception:
            pass

    # Fallback: SerpAPI
    serpapi_key = os.getenv("SERPAPI_KEY")
    if serpapi_key:
        try:
            return await _serpapi_search(query, max_results, serpapi_key)
        except Exception:
            pass

    # Fallback: DuckDuckGo (no key needed)
    try:
        return await _ddg_search(query, max_results)
    except Exception as e:
        return {"results": [], "error": str(e)}


async def _tinyfish_search(query: str, max_results: int, api_key: str) -> dict[str, Any]:
    """Search via TinyFish API."""
    from tinyfish import AsyncTinyFish

    client = AsyncTinyFish(api_key=api_key)
    resp = await client.search.query(query=query)
    results = []
    for r in resp.results[:max_results]:
        results.append(
            {
                "title": r.title,
                "url": r.url,
                "snippet": r.snippet,
            }
        )
    return {"results": results}


async def _serpapi_search(query: str, max_results: int, api_key: str) -> dict[str, Any]:
    """Search via SerpAPI."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://serpapi.com/search",
            params={"q": query, "num": max_results, "api_key": api_key, "engine": "google"},
        )
        data = resp.json()
        results = []
        for r in data.get("organic_results", [])[:max_results]:
            results.append(
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("snippet", ""),
                }
            )
        return {"results": results}


async def _ddg_search(query: str, max_results: int) -> dict[str, Any]:
    """Search via DuckDuckGo (HTML scraping fallback)."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://html.duckduckgo.com/html/",
            params={"q": query},
            headers={"User-Agent": "Mozilla/5.0"},
            follow_redirects=True,
        )
        # Basic HTML parsing (no bs4 dependency)
        text = resp.text
        results = []
        import re

        for match in re.finditer(r'class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>', text):
            url = match.group(1)
            title = re.sub(r"<[^>]+>", "", match.group(2)).strip()
            if url and title:
                results.append({"title": title, "url": url, "snippet": ""})
            if len(results) >= max_results:
                break
        return {"results": results}


async def web_fetch_impl(url: str) -> dict[str, Any]:
    """Fetch and extract content from a URL."""
    # Try TinyFish first
    api_key = os.getenv("TINYFISH_API_KEY")
    if api_key:
        try:
            from tinyfish import AsyncTinyFish

            client = AsyncTinyFish(api_key=api_key)
            resp = await client.fetch.get_contents(urls=[url], format="markdown")
            if resp.results:
                r = resp.results[0]
                return {
                    "title": r.title or "",
                    "description": r.description or "",
                    "text": r.text or "",
                    "format": "markdown",
                }
        except Exception:
            pass

    # Fallback: basic HTTP fetch
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
        return {
            "title": "",
            "description": "",
            "text": resp.text[:50000],
            "format": "html",
        }


# ──────────────────────────────────────────────
# REST Server
# ──────────────────────────────────────────────


async def run_server(host: str = "0.0.0.0", port: int = 8052) -> None:
    """Run the tools server."""
    try:
        from aiohttp import web
    except ImportError:
        print("aiohttp required: pip install aiohttp")
        sys.exit(1)

    async def handle_search(request: web.Request) -> web.Response:
        body = await request.json()
        result = await web_search_impl(
            query=body.get("query", ""),
            max_results=body.get("max_results", 5),
        )
        return web.json_response(result)

    async def handle_fetch(request: web.Request) -> web.Response:
        body = await request.json()
        result = await web_fetch_impl(url=body.get("url", ""))
        return web.json_response(result)

    async def handle_health(request: web.Request) -> web.Response:
        return web.json_response(
            {
                "status": "ok",
                "tools_available": ["web_search", "web_fetch"],
            }
        )

    app = web.Application()
    app.router.add_post("/api/tools/web-search", handle_search)
    app.router.add_post("/api/tools/web-fetch", handle_fetch)
    app.router.add_get("/api/tools/health", handle_health)

    print(f"Tools server running on http://{host}:{port}")
    web.run_app(app, host=host, port=port)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="REST Tools Server")
    parser.add_argument("--port", type=int, default=8052)
    parser.add_argument("--host", type=str, default="0.0.0.0")
    args = parser.parse_args()

    asyncio.run(run_server(host=args.host, port=args.port))
