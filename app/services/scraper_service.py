"""Career Scraper Service — TinyFish primary, Kimi WebBridge / Crawl4AI fallbacks.

All scrapers inherit from BaseCareerScraper which provides the template method
scrape_careers(): normalise URL, iterate career paths, fetch content, check for
keywords, homepage fallback. Subclasses only implement _fetch_content().
"""

import asyncio
import os
from abc import ABC, abstractmethod
from urllib.parse import urljoin

try:
    import logfire
except ImportError:
    logfire = None

from loguru import logger
from tinyfish import APIError, AsyncTinyFish
from tinyfish.search.types import SearchResult

from app.services.career_scraper import CAREER_KEYWORDS, CAREER_PATHS


def _span(name: str, **kwargs):
    if logfire is not None:
        return logfire.span(name, **kwargs)
    from contextlib import nullcontext

    return nullcontext()


def _info(event: str, **kwargs):
    if logfire is not None:
        logfire.info(event, **kwargs)


def _normalise_url(website: str) -> str:
    """Add scheme and strip trailing slash."""
    if not website.startswith(("http://", "https://")):
        website = f"https://{website}"
    return website.rstrip("/")


class BaseCareerScraper(ABC):
    """Abstract base for career page scrapers.

    Subclasses implement _fetch_content() and may override _ensure_ready().
    The template method scrape_careers() handles URL normalisation, career-path
    iteration, keyword matching, and homepage fallback.
    """

    _scraper_tag: str = "scraper"

    @abstractmethod
    async def _fetch_content(self, url: str) -> str | None:
        """Fetch page content from a single URL. Return None on failure or empty page."""
        ...

    async def _ensure_ready(self) -> bool:
        """Override for lazy initialisation / availability check.
        Called once at the start of scrape_careers(). Return True if ready.
        """
        return True

    async def scrape_careers(self, website: str) -> str:
        """Template method: locate and extract a career page."""
        if not await self._ensure_ready():
            return ""

        website = _normalise_url(website)

        with _span(f"{self._scraper_tag}_scrape_careers", website=website):
            for path in CAREER_PATHS:
                content = await self._fetch_content(urljoin(website, path))
                if content and any(kw in content.lower() for kw in CAREER_KEYWORDS):
                    _info(
                        "career_page_found",
                        scraper=self._scraper_tag,
                        website=website,
                        path=path,
                    )
                    return content

            # Homepage fallback
            content = await self._fetch_content(website)
            if content and any(kw in content.lower() for kw in CAREER_KEYWORDS):
                return content

        return ""

    async def scrape_multiple(self, websites: list[str], max_concurrent: int = 5) -> dict[str, str]:
        """Scrape career pages from multiple websites concurrently."""
        if not await self._ensure_ready():
            return {w: "" for w in websites}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scrape(website: str) -> tuple[str, str]:
            async with semaphore:
                content = await self.scrape_careers(website)
                return website, content

        tasks = [_scrape(w) for w in websites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output: dict[str, str] = {}
        for result in results:
            if isinstance(result, tuple):
                website, content = result
                output[website] = content
            else:
                logger.error(f"{self._scraper_tag} scraping error: {result}")
        return output


class TinyFishScraper(BaseCareerScraper):
    """PRIMARY: Cloud API scraper via TinyFish SDK. Free Fetch/Search tier."""

    _scraper_tag = "tinyfish"

    def __init__(self):
        api_key = os.getenv("TINYFISH_API_KEY")
        if not api_key:
            raise ValueError("TINYFISH_API_KEY required for TinyFish scraper")
        self.client = AsyncTinyFish(api_key=api_key)

    async def _fetch_content(self, url: str) -> str | None:
        try:
            resp = await self.client.fetch.get_contents(urls=[url], format="markdown")
            if resp.errors:
                logger.debug(f"TinyFish fetch error for {url}: {resp.errors}")
                return None
            if not resp.results:
                return None
            return resp.results[0].text or None
        except APIError as e:
            logger.debug(f"TinyFish failed for {url}: {e}")
            return None

    async def search_startups(self, query: str, max_results: int = 10) -> list[SearchResult]:
        """Search for startups by criteria (domain, funding, location, etc.)."""
        try:
            resp = await self.client.search.query(query=query)
            return resp.results[:max_results]
        except APIError as e:
            logger.error(f"Startup search failed: {e}")
            return []


class KimiWebBridgeScraper(BaseCareerScraper):
    """FALLBACK: Uses Kimi WebBridge daemon for JS-heavy pages.

    Requires the daemon running locally:
      npx kimi-webbridge
    """

    _scraper_tag = "kimi"
    BASE_URL = "http://127.0.0.1:10086/command"

    def __init__(self):
        self._ready: bool | None = None

    async def _ensure_ready(self) -> bool:
        if self._ready is not None:
            return self._ready
        try:
            import httpx

            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.post(
                    self.BASE_URL,
                    json={"command": "navigate", "url": "about:blank"},
                )
                self._ready = resp.status_code < 500
        except Exception:
            self._ready = False
        if not self._ready:
            logger.warning("Kimi WebBridge daemon not reachable at http://127.0.0.1:10086")
        return self._ready

    async def _fetch_content(self, url: str) -> str | None:
        import httpx

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                nav_resp = await client.post(
                    self.BASE_URL,
                    json={"command": "navigate", "url": url},
                )
                if nav_resp.status_code >= 400:
                    return None

                await asyncio.sleep(2)

                snap_resp = await client.post(
                    self.BASE_URL,
                    json={"command": "snapshot"},
                )
                if snap_resp.status_code >= 400:
                    return None

                data = snap_resp.json()
                return (data.get("content") or data.get("text")) or None
            except Exception as e:
                logger.debug(f"Kimi WebBridge failed for {url}: {e}")
                return None


class Crawl4AIScraper(BaseCareerScraper):
    """OPTIONAL: Local Playwright-based scraper. Free, no API key, needs Chromium."""

    _scraper_tag = "crawl4ai"

    def __init__(self):
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

            self._AsyncWebCrawler = AsyncWebCrawler
            self._BrowserConfig = BrowserConfig
            self._CrawlerRunConfig = CrawlerRunConfig
            self._ready = True
        except ImportError:
            self._ready = False
            logger.warning(
                "crawl4ai not installed. Install with: pip install crawl4ai && crawl4ai-setup"
            )

    async def _ensure_ready(self) -> bool:
        return self._ready

    async def _fetch_content(self, url: str) -> str | None:
        if not self._ready:
            return None

        browser_config = self._BrowserConfig(headless=True, verbose=False)
        async with self._AsyncWebCrawler(config=browser_config) as crawler:
            try:
                result = await crawler.arun(
                    url,
                    config=self._CrawlerRunConfig(
                        word_count_threshold=50,
                        bypass_cache=False,
                    ),
                )
                if result.success and result.markdown:
                    return result.markdown
                return None
            except Exception as e:
                logger.debug(f"Crawl4AI failed for {url}: {e}")
                return None


def get_scraper() -> BaseCareerScraper:
    """Factory: TinyFish by default, Crawl4AI / Kimi WebBridge as fallbacks.

    Priority: TinyFish -> Crawl4AI (if installed) -> Kimi WebBridge (last resort).
    Set USE_CRAWL4AI=true to skip TinyFish and use Crawl4AI directly.
    Set USE_KIMI=true to skip TinyFish and use Kimi WebBridge directly.

    Note: Daemon availability is checked lazily at scrape time via _ensure_ready().
    """
    mode = os.getenv("USE_CRAWL4AI", "").lower()
    if mode == "true":
        return Crawl4AIScraper()

    mode = os.getenv("USE_KIMI", "").lower()
    if mode == "true":
        return KimiWebBridgeScraper()

    try:
        return TinyFishScraper()
    except (ImportError, ValueError) as e:
        logger.warning(f"TinyFish unavailable ({e}), trying Crawl4AI")

    crawl4ai = Crawl4AIScraper()
    if crawl4ai._ready:
        return crawl4ai

    logger.warning("Crawl4AI not available, falling back to Kimi WebBridge")
    return KimiWebBridgeScraper()
