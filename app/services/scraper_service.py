"""Career Scraper Service — TinyFish primary, Crawl4AI optional fallback."""

import asyncio
import os
from abc import ABC, abstractmethod
from typing import List
from urllib.parse import urljoin

try:
    import logfire
except ImportError:
    logfire = None

from loguru import logger

from app.services.career_scraper import CAREER_KEYWORDS, CAREER_PATHS


def _span(name: str, **kwargs):
    if logfire is not None:
        return logfire.span(name, **kwargs)
    from contextlib import nullcontext

    return nullcontext()


def _info(event: str, **kwargs):
    if logfire is not None:
        logfire.info(event, **kwargs)


class BaseCareerScraper(ABC):
    """Abstract base for career page scrapers."""

    @abstractmethod
    async def scrape_careers(self, website: str) -> str:
        """Scrape career page content from a website."""
        ...

    @abstractmethod
    async def scrape_multiple(self, websites: List[str], max_concurrent: int = 5) -> dict[str, str]:
        """Scrape career pages from multiple websites concurrently."""
        ...


class TinyFishScraper(BaseCareerScraper):
    """PRIMARY: Cloud API scraper. Free Fetch/Search tier, no browser install."""

    def __init__(self):
        try:
            from tinyfish import TinyFishClient
        except ImportError:
            raise ImportError("tinyfish not installed. Install with: pip install tinyfish")
        api_key = os.getenv("TINYFISH_API_KEY")
        if not api_key:
            raise ValueError("TINYFISH_API_KEY required for TinyFish scraper")
        self.client = TinyFishClient(api_key=api_key)

    async def scrape_careers(self, website: str) -> str:
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        website = website.rstrip("/")

        with _span("tinyfish_scrape_careers", website=website):
            for path in CAREER_PATHS:
                url = urljoin(website, path)
                try:
                    result = await self.client.fetch(url=url, output_format="markdown")
                    if result and any(kw in result.lower() for kw in CAREER_KEYWORDS):
                        _info("career_page_found", website=website, path=path)
                        return result
                except Exception as e:
                    logger.debug(f"TinyFish failed for {url}: {e}")
        return ""

    async def scrape_multiple(self, websites: List[str], max_concurrent: int = 5) -> dict[str, str]:
        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scrape(website: str) -> tuple[str, str]:
            async with semaphore:
                content = await self.scrape_careers(website)
                return website, content

        tasks = [_scrape(w) for w in websites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for result in results:
            if isinstance(result, tuple):
                website, content = result
                output[website] = content
            else:
                logger.error(f"TinyFish scraping error: {result}")
        return output


class Crawl4AIScraper(BaseCareerScraper):
    """OPTIONAL: Local Playwright-based scraper. Free, no API key, needs Chromium."""

    def __init__(self):
        try:
            from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

            self._AsyncWebCrawler = AsyncWebCrawler
            self._BrowserConfig = BrowserConfig
            self._CrawlerRunConfig = CrawlerRunConfig
            self._available = True
        except ImportError:
            self._available = False
            logger.warning(
                "crawl4ai not installed. Install with: pip install crawl4ai && crawl4ai-setup"
            )

    async def scrape_careers(self, website: str) -> str:
        if not self._available:
            return ""

        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        website = website.rstrip("/")

        with _span("crawl4ai_scrape_careers", website=website):
            browser_config = self._BrowserConfig(headless=True, verbose=False)

            async with self._AsyncWebCrawler(config=browser_config) as crawler:
                for path in CAREER_PATHS:
                    url = urljoin(website, path)
                    try:
                        result = await crawler.arun(
                            url,
                            config=self._CrawlerRunConfig(
                                word_count_threshold=50,
                                bypass_cache=False,
                            ),
                        )
                        if result.success and result.markdown:
                            content_lower = result.markdown.lower()
                            if any(kw in content_lower for kw in CAREER_KEYWORDS):
                                return result.markdown
                    except Exception as e:
                        logger.debug(f"Crawl4AI failed for {url}: {e}")

                # Try homepage as fallback
                try:
                    result = await crawler.arun(website)
                    if result.success and result.markdown:
                        content_lower = result.markdown.lower()
                        if any(kw in content_lower for kw in CAREER_KEYWORDS):
                            return result.markdown
                except Exception as e:
                    logger.debug(f"Crawl4AI homepage failed for {website}: {e}")

        return ""

    async def scrape_multiple(self, websites: List[str], max_concurrent: int = 5) -> dict[str, str]:
        if not self._available:
            return {w: "" for w in websites}

        semaphore = asyncio.Semaphore(max_concurrent)

        async def _scrape(website: str) -> tuple[str, str]:
            async with semaphore:
                content = await self.scrape_careers(website)
                return website, content

        tasks = [_scrape(w) for w in websites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for result in results:
            if isinstance(result, tuple):
                website, content = result
                output[website] = content
            else:
                logger.error(f"Crawl4AI scraping error: {result}")
        return output


def get_scraper() -> BaseCareerScraper:
    """Factory: TinyFish by default, Crawl4AI as fallback if USE_CRAWL4AI=true."""
    if os.getenv("USE_CRAWL4AI", "").lower() == "true":
        return Crawl4AIScraper()
    try:
        return TinyFishScraper()
    except (ImportError, ValueError) as e:
        logger.warning(f"TinyFish unavailable ({e}), falling back to Crawl4AI")
        return Crawl4AIScraper()
