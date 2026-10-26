"""Polite Wayback Machine client: CDX lookups and raw capture retrieval."""

from __future__ import annotations

import gzip
import os
import time
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

load_dotenv()

CDX_ENDPOINT = "https://web.archive.org/cdx/search/cdx"
# The id_ flag returns the archived bytes without the Wayback toolbar or link rewriting.
RAW_CAPTURE = "https://web.archive.org/web/{timestamp}id_/{url}"

DEFAULT_USER_AGENT = "VolLineage COSC445 (University of Tennessee course project)"


@dataclass(frozen=True)
class Capture:
    original: str
    timestamp: str
    digest: str
    length: int

    @property
    def raw_url(self) -> str:
        return RAW_CAPTURE.format(timestamp=self.timestamp, url=self.original)


class WaybackClient:
    def __init__(self, min_interval: float = 1.5, retries: int = 4, timeout: float = 90):
        self.session = requests.Session()
        self.session.headers["User-Agent"] = os.getenv("VOLLINEAGE_USER_AGENT", DEFAULT_USER_AGENT)
        self.min_interval = min_interval
        self.retries = retries
        self.timeout = timeout
        self._last_request = 0.0
        self.request_count = 0

    def _get(self, url: str, params: dict | None = None) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(self.retries):
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            self.request_count += 1
            try:
                response = self.session.get(url, params=params, timeout=self.timeout)
            except requests.RequestException as exc:
                last_error = exc
            else:
                if response.status_code == 200:
                    return response
                last_error = RuntimeError(f"HTTP {response.status_code} for {response.url}")
                if response.status_code not in (429, 500, 502, 503, 504):
                    break
            time.sleep(2 ** (attempt + 1))
        raise RuntimeError(f"Wayback request failed: {url}") from last_error

    def cdx(self, url: str, **params) -> list[Capture]:
        """Unique status-200 captures of one URL, oldest first."""
        query = {
            "url": url,
            "output": "json",
            "filter": "statuscode:200",
            "collapse": "digest",
            "fl": "original,timestamp,digest,length",
            **params,
        }
        rows = self._get(CDX_ENDPOINT, params=query).json()
        if not rows:
            return []
        header, *body = rows
        out = []
        for row in body:
            record = dict(zip(header, row))
            out.append(
                Capture(
                    original=record["original"],
                    timestamp=record["timestamp"],
                    digest=record["digest"],
                    length=int(record["length"]) if record["length"].isdigit() else 0,
                )
            )
        return out

    def count_unique(self, url: str, **params) -> int:
        """Number of unique status-200 captures for a URL pattern."""
        query = {
            "url": url,
            "filter": "statuscode:200",
            "collapse": "digest",
            "fl": "timestamp",
            **params,
        }
        text = self._get(CDX_ENDPOINT, params=query).text
        return sum(1 for line in text.splitlines() if line.strip())

    def fetch(self, capture: Capture) -> bytes:
        body = self._get(capture.raw_url).content
        # Some captures were archived gzip-encoded and come back without a Content-Encoding header.
        if body[:2] == b"\x1f\x8b":
            body = gzip.decompress(body)
        return body
