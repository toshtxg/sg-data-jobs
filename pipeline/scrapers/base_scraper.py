import abc
import time
import logging

import requests

logger = logging.getLogger(__name__)

# (connect, read) seconds. MCF often takes >15s to answer a cold 100-result
# query, so a short read timeout made every retry time out the same way.
REQUEST_TIMEOUT = (10, 45)
# After this many requests in a row exhaust their retries, treat the source as
# down and skip its remaining requests so the run stays inside the job timeout.
MAX_CONSECUTIVE_FAILED_REQUESTS = 3


class BaseScraper(abc.ABC):
    """Abstract base for all job scrapers."""

    source_name: str = ""

    def __init__(self, delay: float = 2.0):
        self.delay = delay
        self._first_request = True
        self._consecutive_failed_requests = 0
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "SGAIJobScout/1.0 (research project)",
                "Accept": "application/json",
            }
        )

    @abc.abstractmethod
    def scrape(
        self,
        search_term: str,
        max_pages: int = 5,
        known_urls: set[str] | None = None,
    ) -> list[dict]:
        """Return list of normalized job dicts for a single search term."""
        ...

    def scrape_all(
        self,
        search_terms: list[str],
        max_pages: int = 5,
        known_urls: set[str] | None = None,
    ) -> list[dict]:
        """Scrape across all search terms, deduplicating by source_url."""
        all_jobs: dict[str, dict] = {}
        for term in search_terms:
            try:
                jobs = self.scrape(term, max_pages, known_urls)
                for job in jobs:
                    all_jobs[job["source_url"]] = job
                logger.info(f"[{self.source_name}] '{term}': {len(jobs)} jobs found")
            except Exception as e:
                logger.error(f"[{self.source_name}] '{term}' failed: {e}")
        logger.info(
            f"[{self.source_name}] Total unique jobs: {len(all_jobs)}"
        )
        return list(all_jobs.values())

    def _request_with_backoff(
        self,
        url: str,
        params: dict | None = None,
        max_retries: int = 3,
    ) -> requests.Response | None:
        """GET request with exponential backoff on failure."""
        if self._consecutive_failed_requests >= MAX_CONSECUTIVE_FAILED_REQUESTS:
            return None
        # Politeness delay between requests — sleep before each request except
        # the very first, so we never sleep after the final request of a run.
        if not self._first_request and self.delay > 0:
            time.sleep(self.delay)
        self._first_request = False
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                resp.raise_for_status()
                self._consecutive_failed_requests = 0
                return resp
            except requests.RequestException as e:
                wait = 2 ** attempt
                logger.warning(
                    f"[{self.source_name}] Retry {attempt + 1}/{max_retries} "
                    f"after {wait}s: {e}"
                )
                time.sleep(wait)
        logger.error(f"[{self.source_name}] All {max_retries} retries failed for {url}")
        self._consecutive_failed_requests += 1
        if self._consecutive_failed_requests >= MAX_CONSECUTIVE_FAILED_REQUESTS:
            logger.error(
                f"[{self.source_name}] {self._consecutive_failed_requests} "
                "requests failed in a row — skipping remaining requests this run"
            )
        return None

    @staticmethod
    def normalize_job(
        source: str,
        source_url: str,
        title: str,
        company: str | None,
        description: str | None,
        salary_min: float | None,
        salary_max: float | None,
        posting_date: str | None,
        raw_data: dict | None = None,
        expiry_date: str | None = None,
        original_posting_date: str | None = None,
    ) -> dict:
        """Create a standardized job dict matching raw_listings schema."""
        return {
            "source": source,
            "source_url": source_url,
            "title": title,
            "company": company,
            "description": description,
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "SGD",
            "posting_date": posting_date,
            "expiry_date": expiry_date,
            "original_posting_date": original_posting_date,
            "raw_data": raw_data,
        }
