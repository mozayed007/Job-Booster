"""Career Scraper Service - Scrapes career pages using Crawl4AI."""

import asyncio
from typing import Any
from urllib.parse import urljoin

from loguru import logger

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
    logger.warning("Crawl4AI not installed. Run: pip install crawl4ai")

logfire: Any = None
try:
    import logfire as _logfire

    logfire = _logfire
except ImportError:
    pass


def _span(name: str, **kwargs):
    if logfire is not None:
        return logfire.span(name, **kwargs)
    from contextlib import nullcontext

    return nullcontext()


def _info(event: str, **kwargs):
    if logfire is not None:
        logfire.info(event, **kwargs)


# Common career page paths to try
CAREER_PATHS = [
    "/careers",
    "/jobs",
    "/join-us",
    "/work-with-us",
    "/about/careers",
    "/company/careers",
    "/hiring",
    "/opportunities",
]

# Keywords that indicate a career page
CAREER_KEYWORDS = [
    "career",
    "job",
    "position",
    "opening",
    "hiring",
    "join us",
    "work with us",
    "apply",
    "vacancy",
]


class CareerScraper:
    """Scrapes career pages from startup websites using Crawl4AI."""

    def __init__(
        self,
        headless: bool = True,
        timeout: int = 30000,  # 30 seconds
        word_count_threshold: int = 50,
    ):
        self.headless = headless
        self.timeout = timeout
        self.word_count_threshold = word_count_threshold

    async def _try_career_url(
        self, crawler: "AsyncWebCrawler", base_url: str, path: str
    ) -> str | None:
        """Try to scrape a single career URL path."""
        url = urljoin(base_url, path)

        try:
            result = await crawler.arun(
                url,
                config=CrawlerRunConfig(
                    word_count_threshold=self.word_count_threshold,
                    bypass_cache=False,
                ),
            )

            if result.success and result.markdown:
                # Check if page has career-related content
                content_lower = result.markdown.lower()
                if any(kw in content_lower for kw in CAREER_KEYWORDS):
                    logger.debug(f"Found career page: {url}")
                    return str(result.markdown)
        except Exception as e:
            logger.debug(f"Failed to scrape {url}: {e}")

        return None

    async def scrape_careers(self, website: str) -> str:
        """
        Scrape career page content from a startup website.

        Args:
            website: Base URL of the startup (e.g., "https://example.com")

        Returns:
            Markdown-formatted career page content, or empty string if not found
        """
        if not CRAWL4AI_AVAILABLE:
            logger.error("Crawl4AI not available")
            return ""

        # Normalize URL
        if not website.startswith(("http://", "https://")):
            website = f"https://{website}"
        website = website.rstrip("/")

        with _span("scrape_careers", website=website):
            browser_config = BrowserConfig(
                headless=self.headless,
                verbose=False,
            )

            async with AsyncWebCrawler(config=browser_config) as crawler:
                # Try each career path
                for path in CAREER_PATHS:
                    content = await self._try_career_url(crawler, website, path)
                    if content:
                        _info(
                            "career_page_found",
                            website=website,
                            path=path,
                            content_length=len(content),
                        )
                        return content

                # Try the homepage as fallback
                try:
                    result = await crawler.arun(website)
                    if result.success and result.markdown:
                        # Look for career links in homepage
                        content_lower = result.markdown.lower()
                        if any(kw in content_lower for kw in CAREER_KEYWORDS):
                            _info("career_content_in_homepage", website=website)
                            return str(result.markdown)
                except Exception as e:
                    logger.debug(f"Failed to scrape homepage {website}: {e}")

        _info("no_career_page", website=website)
        return ""

    async def scrape_multiple(
        self,
        websites: list[str],
        max_concurrent: int = 5,
    ) -> dict[str, str]:
        """
        Scrape career pages from multiple websites concurrently.

        Args:
            websites: List of startup website URLs
            max_concurrent: Maximum concurrent scrapes

        Returns:
            Dict mapping website to career page content
        """
        semaphore = asyncio.Semaphore(max_concurrent)

        async def scrape_with_semaphore(website: str) -> tuple[str, str]:
            async with semaphore:
                content = await self.scrape_careers(website)
                return website, content

        tasks = [scrape_with_semaphore(w) for w in websites]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        output = {}
        for result in results:
            if isinstance(result, tuple):
                website, content = result
                output[website] = content
            else:
                logger.error(f"Scraping error: {result}")

        return output


# Convenience function for simple usage
async def scrape_startup_careers(website: str) -> str:
    """Scrape career page from a single startup website."""
    scraper = CareerScraper()
    return await scraper.scrape_careers(website)


if __name__ == "__main__":
    # Quick test
    import asyncio

    async def test():
        scraper = CareerScraper()
        content = await scraper.scrape_careers("https://weaviate.io")
        print(f"Content length: {len(content)}")
        print(content[:500] if content else "No content found")

    asyncio.run(test())
