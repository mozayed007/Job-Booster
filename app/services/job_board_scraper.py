"""Multi-source job board scraper for discovering jobs across platforms."""

import asyncio
import os
from abc import ABC, abstractmethod

from loguru import logger

from app.models.job_model import ScrapedJob


class BaseJobBoardScraper(ABC):
    """Abstract base for job board scrapers."""

    @abstractmethod
    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        ...

    @property
    @abstractmethod
    def source_name(self) -> str:
        ...

    @property
    def is_available(self) -> bool:
        return True


class RemoteOKScraper(BaseJobBoardScraper):
    """RemoteOK — free JSON API, no auth needed."""

    @property
    def source_name(self) -> str:
        return "remoteok"

    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        try:
            import httpx

            tag = query.lower().replace(" ", "-")
            url = f"https://remoteok.com/api?tag={tag}"
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, headers={"User-Agent": "JobBooster/1.0"})
                if resp.status_code != 200:
                    logger.warning(f"RemoteOK returned {resp.status_code}")
                    return []
                data = resp.json()
                # First item is metadata, skip it
                jobs = []
                for item in data[1:limit+1]:
                    if not isinstance(item, dict):
                        continue
                    jobs.append(ScrapedJob(
                        title=item.get("position", ""),
                        company=item.get("company", ""),
                        location=item.get("location", "Remote"),
                        url=item.get("url", ""),
                        description=item.get("description", "")[:500],
                        source="remoteok",
                    ))
                return jobs
        except ImportError:
            logger.warning("httpx not installed — RemoteOK scraper unavailable")
            return []
        except Exception as e:
            logger.error(f"RemoteOK scraper error: {e}")
            return []


class AdzunaScraper(BaseJobBoardScraper):
    """Adzuna — free tier (250 calls/month), requires API key."""

    @property
    def source_name(self) -> str:
        return "adzuna"

    @property
    def is_available(self) -> bool:
        return bool(os.getenv("ADZUNA_API_KEY"))

    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        api_key = os.getenv("ADZUNA_API_KEY")
        app_id = os.getenv("ADZUNA_APP_ID", "1")
        if not api_key:
            logger.warning("ADZUNA_API_KEY not set")
            return []

        try:
            import httpx

            url = "https://api.adzuna.com/v1/api/jobs/us/search/1"
            params = {
                "app_id": app_id,
                "app_key": api_key,
                "results_per_page": min(limit, 50),
                "what": query,
                "where": location or "",
                "content-type": "application/json",
            }
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.get(url, params=params)
                if resp.status_code != 200:
                    logger.warning(f"Adzuna returned {resp.status_code}")
                    return []
                data = resp.json()
                jobs = []
                for item in data.get("results", []):
                    jobs.append(ScrapedJob(
                        title=item.get("title", ""),
                        company=item.get("company", {}).get("display_name", ""),
                        location=item.get("location", {}).get("display_name", ""),
                        url=item.get("redirect_url", ""),
                        description=item.get("description", "")[:500],
                        source="adzuna",
                    ))
                return jobs
        except ImportError:
            logger.warning("httpx not installed — Adzuna scraper unavailable")
            return []
        except Exception as e:
            logger.error(f"Adzuna scraper error: {e}")
            return []


class LinkedInRSSScraper(BaseJobBoardScraper):
    """LinkedIn public job RSS feeds — no auth needed."""

    @property
    def source_name(self) -> str:
        return "linkedin"

    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        try:
            import re

            import httpx

            keyword = query.replace(" ", "+")
            url = f"https://www.linkedin.com/jobs/search/?keywords={keyword}"
            if location:
                url += f"&location={location.replace(' ', '+')}"

            # Use the public RSS feed
            count = min(limit, 25)
            rss_url = (
                "https://www.linkedin.com/jobs-guest/jobs/api"
                f"/seeMoreJobPostings/search?keywords={keyword}&start=0&count={count}"
            )
            if location:
                rss_url += f"&location={location.replace(' ', '+')}"

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(rss_url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    logger.warning(f"LinkedIn RSS returned {resp.status_code}")
                    return []

                html = resp.text
                jobs = []
                # Simple regex extraction from LinkedIn's public HTML
                _t = r'base-search-card__title[^"]*"[^>]*>([^<]+)</h3>'
                titles = re.findall(rf'<h3[^>]*class="[^"]*{_t}', html)
                _s = r'base-search-card__subtitle[^"]*"[^>]*>.*?<a[^>]*>([^<]+)</a>'
                companies = re.findall(rf'<h4[^>]*class="[^"]*{_s}', html, re.DOTALL)
                _f = r'base-card__full-link[^"]*"[^>]*href="([^"]+)"'
                links = re.findall(rf'<a[^>]*class="[^"]*{_f}', html)
                _l = r'job-search-card__location[^"]*"[^>]*>([^<]+)</span>'
                locations = re.findall(rf'<span[^>]*class="[^"]*{_l}', html)

                for i in range(min(len(titles), limit)):
                    jobs.append(ScrapedJob(
                        title=titles[i].strip() if i < len(titles) else "",
                        company=companies[i].strip() if i < len(companies) else "",
                        location=locations[i].strip() if i < len(locations) else "",
                        url=links[i].strip() if i < len(links) else "",
                        description="",
                        source="linkedin",
                    ))
                return jobs
        except ImportError:
            logger.warning("httpx not installed — LinkedIn scraper unavailable")
            return []
        except Exception as e:
            logger.error(f"LinkedIn RSS scraper error: {e}")
            return []


class IndeedScraper(BaseJobBoardScraper):
    """Indeed HTML scraping — no API key, uses public search results."""

    @property
    def source_name(self) -> str:
        return "indeed"

    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        try:
            import re

            import httpx

            keyword = query.replace(" ", "+")
            loc = location.replace(" ", "+") if location else ""
            url = f"https://www.indeed.com/jobs?q={keyword}"
            if loc:
                url += f"&l={loc}"

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    logger.warning(f"Indeed returned {resp.status_code}")
                    return []

                html = resp.text
                jobs = []

                # Extract job cards from Indeed HTML
                _card_re = r'<div[^>]*class="[^"]*job_seen_beacon[^"]*"[^>]*>'
                cards = re.findall(
                    rf'{_card_re}(.*?)</div>\s*</div>', html, re.DOTALL,
                )
                for card in cards[:limit]:
                    title_m = re.search(
                        r'<h2[^>]*>.*?<a[^>]*>(.*?)</a>', card, re.DOTALL,
                    )
                    company_m = re.search(
                        r'<span[^>]*data-testid="company-name"[^>]*>'
                        r'(.*?)</span>', card,
                    )
                    location_m = re.search(
                        r'<div[^>]*data-testid="text-location"[^>]*>'
                        r'(.*?)</div>', card,
                    )
                    link_m = re.search(r'<a[^>]*href="(/viewjob[^"]*)"', card)

                    def _clean(x, m):
                        return re.sub(r'<[^>]+>', '', m.group(1)).strip() if m else x
                    title = _clean("", title_m)
                    company = _clean("", company_m)
                    loc_str = _clean("", location_m)
                    link = f"https://www.indeed.com{link_m.group(1)}" if link_m else ""

                    if title:
                        jobs.append(ScrapedJob(
                            title=title,
                            company=company,
                            location=loc_str,
                            url=link,
                            description="",
                            source="indeed",
                        ))
                return jobs
        except ImportError:
            logger.warning("httpx not installed — Indeed scraper unavailable")
            return []
        except Exception as e:
            logger.error(f"Indeed scraper error: {e}")
            return []


class WuzzufScraper(BaseJobBoardScraper):
    """Wuzzuf — Egypt-focused job board, public search."""

    @property
    def source_name(self) -> str:
        return "wuzzuf"

    async def search(self, query: str, location: str = "", limit: int = 20) -> list[ScrapedJob]:
        try:
            import re

            import httpx

            keyword = query.replace(" ", "+")
            url = f"https://wuzzuf.net/search/jobs/?q={keyword}"
            if location:
                url += f"&l={location.replace(' ', '+')}"

            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
                if resp.status_code != 200:
                    logger.warning(f"Wuzzuf returned {resp.status_code}")
                    return []

                html = resp.text
                jobs = []

                _t = r'css-m604qf[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>'
                titles = re.findall(
                    rf'<h2[^>]*class="[^"]*{_t}', html, re.DOTALL,
                )
                _c = r'css-17s97q8[^"]*"[^>]*>(.*?)</a>'
                companies = re.findall(rf'<a[^>]*class="[^"]*{_c}', html)
                _l = r'css-5wys0k[^"]*"[^>]*>(.*?)</span>'
                locations = re.findall(rf'<span[^>]*class="[^"]*{_l}', html)
                links = re.findall(
                    r'<h2[^>]*>.*?<a[^>]*href="([^"]+)"', html, re.DOTALL,
                )

                for i in range(min(len(titles), limit)):
                    def _strip(x):
                        return re.sub(r'<[^>]+>', '', x).strip() if x else ""
                    title = _strip(titles[i] if i < len(titles) else "")
                    company = _strip(companies[i] if i < len(companies) else "")
                    loc_str = _strip(locations[i] if i < len(locations) else "")
                    link = f"https://wuzzuf.net{links[i]}" if i < len(links) else ""

                    if title:
                        jobs.append(ScrapedJob(
                            title=title,
                            company=company,
                            location=loc_str,
                            url=link,
                            description="",
                            source="wuzzuf",
                        ))
                return jobs
        except ImportError:
            logger.warning("httpx not installed — Wuzzuf scraper unavailable")
            return []
        except Exception as e:
            logger.error(f"Wuzzuf scraper error: {e}")
            return []


SCRAPERS: dict[str, type[BaseJobBoardScraper]] = {
    "remoteok": RemoteOKScraper,
    "adzuna": AdzunaScraper,
    "linkedin": LinkedInRSSScraper,
    "indeed": IndeedScraper,
    "wuzzuf": WuzzufScraper,
}


def get_available_sources() -> dict[str, bool]:
    """Return which sources are available."""
    result = {}
    for name, cls in SCRAPERS.items():
        try:
            instance = cls()
            result[name] = instance.is_available
        except Exception:
            result[name] = False
    return result


async def search_all_sources(
    query: str,
    location: str = "",
    limit: int = 20,
    sources: list[str] | None = None,
) -> dict[str, list[ScrapedJob]]:
    """Search across multiple job boards concurrently."""
    if sources is None:
        sources = list(SCRAPERS.keys())

    results: dict[str, list[ScrapedJob]] = {}

    async def _search_one(name: str):
        cls = SCRAPERS.get(name)
        if not cls:
            return
        try:
            scraper = cls()
            if not scraper.is_available:
                results[name] = []
                return
            jobs = await scraper.search(query, location, limit)
            results[name] = jobs
        except Exception as e:
            logger.error(f"Scraper {name} error: {e}")
            results[name] = []

    tasks = [_search_one(s) for s in sources if s in SCRAPERS]
    await asyncio.gather(*tasks, return_exceptions=True)
    return results
