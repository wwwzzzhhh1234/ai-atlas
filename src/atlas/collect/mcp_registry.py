"""Official MCP Registry collector (spec Section 7, source 2).

Lists the latest version of every active server. Servers with a GitHub repository become
`gh:owner/repo` stubs (metadata filled by the GitHub lookup and merged by id);
servers without one become `mcp:<registry name>` records.
"""

from __future__ import annotations

import logging
import re

from atlas.collect.common import iso_date, new_record
from atlas.config import load_config
from atlas.http import CachedClient

log = logging.getLogger(__name__)
_GH_RE = re.compile(r"github\.com[/:]([A-Za-z0-9-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?/?$")


def client() -> CachedClient:
    c = load_config("sources")
    return CachedClient("mcp_registry", headers={"User-Agent": "ai-atlas-collector"},
                        min_interval=c["mcp_registry"]["min_interval_seconds"],
                        max_retries=c["http"]["max_retries"], backoff_base=c["http"]["backoff_base_seconds"],
                        timeout=c["http"]["timeout_seconds"])


def github_full_name(url: str | None) -> str | None:
    if not url:
        return None
    m = _GH_RE.search(url.strip())
    return f"{m.group(1)}/{m.group(2)}" if m else None


def server_record(entry: dict) -> dict | None:
    srv = entry.get("server", {})
    meta = entry.get("_meta", {}).get("io.modelcontextprotocol.registry/official", {})
    if meta.get("status", "active") != "active":
        return None
    repo = github_full_name((srv.get("repository") or {}).get("url"))
    if repo:
        return new_record("gh:" + repo.lower(), source="mcp_registry", group="mcp_registry", full_name=repo)
    return new_record(
        f"mcp:{srv['name']}", source="mcp_registry", group="mcp_registry",
        name=srv.get("title") or srv["name"], description=srv.get("description"),
        url=srv.get("websiteUrl"), created_at=iso_date(meta.get("publishedAt")),
        pushed_at=iso_date(meta.get("updatedAt")), is_fork=False, is_archived=False, has_readme=False,
    )


def collect(c: CachedClient, max_pages: int | None = None) -> list[dict]:
    cfg = load_config("sources")["mcp_registry"]
    url = f"{cfg['base_url']}/{cfg['api_version']}/servers"
    out, cursor, pages = [], None, 0
    while True:
        params = {"limit": cfg["page_size"], "version": "latest"}
        if cursor:
            params["cursor"] = cursor
        r = c.get(url, params=params)
        if r.status != 200:
            log.error("MCP registry page failed (%d), stopping at %d pages", r.status, pages)
            break
        data = r.json()
        out += [rec for e in data.get("servers", []) if (rec := server_record(e))]
        pages += 1
        cursor = (data.get("metadata") or {}).get("nextCursor")
        if not cursor or (max_pages and pages >= max_pages):
            break
    log.info("MCP registry: %d pages -> %d active servers", pages, len(out))
    return out
