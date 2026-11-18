"""HTTP fetching with retries, exponential backoff and a polite delay."""

from __future__ import annotations

import logging
import time

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

log = logging.getLogger(__name__)

DEFAULT_USER_AGENT = "portfolio-demo/1.0 (+https://github.com/rycex1)"


def build_session(
    retries: int = 4,
    backoff: float = 1.0,
    user_agent: str = DEFAULT_USER_AGENT,
) -> requests.Session:
    """Return a session that retries transient failures with exponential backoff.

    With backoff=1.0 the waits between attempts are roughly 1s, 2s, 4s, 8s.
    """
    retry = Retry(
        total=retries,
        backoff_factor=backoff,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET", "HEAD"),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers["User-Agent"] = user_agent
    return session


class Fetcher:
    """Fetches pages through one session, sleeping `delay` seconds between requests."""

    def __init__(self, session: requests.Session | None = None, delay: float = 0.5, timeout: float = 15.0):
        self.session = session or build_session()
        self.delay = delay
        self.timeout = timeout
        self._last_request = 0.0

    def get(self, url: str) -> str | None:
        """Return the page body, or None for a 404. Raises on other HTTP errors."""
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        log.debug("GET %s", url)
        resp = self.session.get(url, timeout=self.timeout)
        self._last_request = time.monotonic()
        if resp.status_code == 404:
            log.info("404 for %s, stopping", url)
            return None
        resp.raise_for_status()
        resp.encoding = "utf-8"  # the site is UTF-8 but does not always say so
        return resp.text
