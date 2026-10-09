"""Tests for BaseScraper._request_with_backoff timeout and give-up behaviour.

No network is used: the requests session and time.sleep are monkeypatched.
"""

import requests

from pipeline.scrapers import base_scraper
from pipeline.scrapers.mycareersfuture import MyCareersFutureScraper


class _OkResponse:
    def raise_for_status(self):
        pass


def _scraper(monkeypatch, outcomes):
    """Scraper whose session.get pops results from `outcomes` (exception or response)."""
    monkeypatch.setattr(base_scraper.time, "sleep", lambda _s: None)
    scraper = MyCareersFutureScraper()
    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(timeout)
        outcome = outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome

    scraper.session.get = fake_get
    return scraper, calls


def test_request_uses_long_read_timeout(monkeypatch):
    scraper, calls = _scraper(monkeypatch, [_OkResponse()])
    assert scraper._request_with_backoff("u") is not None
    assert calls == [base_scraper.REQUEST_TIMEOUT]
    assert base_scraper.REQUEST_TIMEOUT[1] > 15


def test_retry_then_success_resets_failure_count(monkeypatch):
    timeout = requests.exceptions.ReadTimeout("slow")
    scraper, calls = _scraper(monkeypatch, [timeout, _OkResponse()])
    assert scraper._request_with_backoff("u") is not None
    assert len(calls) == 2
    assert scraper._consecutive_failed_requests == 0


def test_gives_up_after_consecutive_failed_requests(monkeypatch):
    limit = base_scraper.MAX_CONSECUTIVE_FAILED_REQUESTS
    timeout = requests.exceptions.ReadTimeout("slow")
    scraper, calls = _scraper(monkeypatch, [timeout] * (3 * limit))

    for _ in range(limit):
        assert scraper._request_with_backoff("u", max_retries=3) is None
    assert len(calls) == 3 * limit

    # Source is treated as down: further requests return without hitting it
    assert scraper._request_with_backoff("u") is None
    assert len(calls) == 3 * limit


def test_a_success_between_failures_keeps_scraping(monkeypatch):
    limit = base_scraper.MAX_CONSECUTIVE_FAILED_REQUESTS
    timeout = requests.exceptions.ReadTimeout("slow")
    outcomes = [timeout] * (limit - 1) + [_OkResponse()] + [timeout] * (limit - 1)
    scraper, _calls = _scraper(monkeypatch, outcomes)

    for _ in range(limit - 1):
        assert scraper._request_with_backoff("u", max_retries=1) is None
    assert scraper._request_with_backoff("u", max_retries=1) is not None
    for _ in range(limit - 1):
        assert scraper._request_with_backoff("u", max_retries=1) is None
    assert scraper._consecutive_failed_requests == limit - 1
