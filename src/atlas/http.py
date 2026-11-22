"""HTTP client with a permanent on-disk cache, throttling and backoff.

Every successful (200) or definitive-miss (404) response is saved as gzipped JSON under
data/cache/http/<namespace>/<sha256>.json.gz, so re-running a collector never re-fetches it.
Rate-limit (403/429) and server errors (5xx) are retried with backoff and never cached.
Secrets: the Authorization header is never written to the cache or the log.
"""

from __future__ import annotations

import gzip
import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import httpx

from atlas.paths import CACHE_DIR

log = logging.getLogger(__name__)

CACHEABLE = {200, 404}
RETRYABLE = {403, 429, 500, 502, 503, 504}
MAX_SLEEP_SECONDS = 900


@dataclass
class Response:
    status: int
    text: str
    headers: dict[str, str]
    url: str
    from_cache: bool = False

    def json(self) -> Any:
        return json.loads(self.text)


@dataclass
class Stats:
    network_calls: int = 0
    cache_hits: int = 0
    errors: int = 0
    by_namespace: dict[str, list[int]] = field(default_factory=dict)  # ns -> [network, cache]

    def add(self, ns: str, network: bool) -> None:
        with _STATS_LOCK:
            self._add(ns, network)

    def _add(self, ns: str, network: bool) -> None:
        pair = self.by_namespace.setdefault(ns, [0, 0])
        if network:
            self.network_calls += 1
            pair[0] += 1
        else:
            self.cache_hits += 1
            pair[1] += 1


_STATS_LOCK = threading.Lock()
STATS = Stats()


def full_url(url: str, params: dict | None) -> str:
    if not params:
        return url
    return f"{url}{'&' if '?' in url else '?'}{urlencode(params, doseq=True)}"


class CachedClient:
    def __init__(self, namespace: str, *, headers: dict[str, str] | None = None,
                 min_interval: float = 0.0, max_retries: int = 5, backoff_base: float = 2.0,
                 timeout: float = 30.0, cache_dir: Path | None = None,
                 transport: httpx.BaseTransport | None = None):
        self.namespace = namespace
        self.cache_dir = (cache_dir or CACHE_DIR / "http") / namespace
        self.min_interval = min_interval
        self.max_retries = max_retries
        self.backoff_base = backoff_base
        self._last_call = 0.0
        self._lock = threading.Lock()
        self.cacheable = set(CACHEABLE)
        self.retryable = set(RETRYABLE)
        self._client = httpx.Client(headers=headers or {}, timeout=timeout,
                                    follow_redirects=True, transport=transport)

    # ------------------------------------------------------------------ cache
    def _path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.cache_dir / digest[:2] / f"{digest}.json.gz"

    def _load(self, url: str) -> Response | None:
        p = self._path(url)
        if not p.exists():
            return None
        with gzip.open(p, "rt", encoding="utf-8") as f:
            rec = json.load(f)
        return Response(rec["status"], rec["text"], rec["headers"], url, from_cache=True)

    def _save(self, resp: Response) -> None:
        p = self._path(resp.url)
        p.parent.mkdir(parents=True, exist_ok=True)
        rec = {"url": resp.url, "status": resp.status, "headers": resp.headers, "text": resp.text,
               "fetched_at": datetime.now(timezone.utc).isoformat()}
        tmp = p.with_suffix(".tmp")
        with gzip.open(tmp, "wt", encoding="utf-8") as f:
            json.dump(rec, f)
        os.replace(tmp, p)  # atomic: an interrupted run never leaves a half-written cache file

    def is_cached(self, url: str, params: dict | None = None) -> bool:
        return self._path(full_url(url, params)).exists()

    # ------------------------------------------------------------------ network
    def _throttle(self) -> None:
        with self._lock:  # serialize spacing between calls across threads
            wait = self.min_interval - (time.monotonic() - self._last_call)
            if wait > 0:
                time.sleep(wait)
            self._last_call = time.monotonic()

    def _retry_delay(self, resp: httpx.Response, attempt: int) -> float:
        h = resp.headers
        if h.get("retry-after", "").isdigit():
            return float(h["retry-after"]) + 1
        if h.get("x-ratelimit-remaining") == "0" and h.get("x-ratelimit-reset", "").isdigit():
            return max(1.0, float(h["x-ratelimit-reset"]) - time.time() + 2)
        return self.backoff_base * (2 ** attempt)

    def get(self, url: str, params: dict | None = None, headers: dict | None = None) -> Response:
        url = full_url(url, params)
        cached = self._load(url)
        if cached is not None:
            STATS.add(self.namespace, network=False)
            return cached
        for attempt in range(self.max_retries + 1):
            self._throttle()
            try:
                r = self._client.get(url, headers=headers)
            except httpx.TransportError as exc:
                log.warning("%s transport error (%s), attempt %d", self.namespace, exc, attempt + 1)
                time.sleep(self.backoff_base * (2 ** attempt))
                continue
            STATS.add(self.namespace, network=True)
            keep = {k: v for k, v in r.headers.items() if k.lower() in ("link", "content-type")}
            resp = Response(r.status_code, r.text, keep, url)
            if r.status_code in self.cacheable:
                self._save(resp)
                return resp
            if r.status_code in self.retryable and attempt < self.max_retries:
                delay = min(self._retry_delay(r, attempt), MAX_SLEEP_SECONDS)
                log.warning("%s HTTP %d, sleeping %.0fs (attempt %d)", self.namespace,
                            r.status_code, delay, attempt + 1)
                time.sleep(delay)
                continue
            STATS.errors += 1
            return resp
        STATS.errors += 1  # every attempt was a transport error
        return Response(599, "", {}, url)


def github_headers() -> dict[str, str]:
    """Headers for api.github.com. Uses GITHUB_TOKEN from the environment/.env if present."""
    headers = {"Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28",
               "User-Agent": "ai-atlas-collector"}
    token = os.environ.get("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers
