"""GitHub collector (spec Section 7, source 1).

- Repository search (topics + sector keyword groups) with adaptive slicing under the 1,000-result cap.
- Code search for SKILL.md files -> repository names.
- Curated lists -> repository names parsed from their README.
- Metadata for repos found by name: batched `repo:a/b repo:c/d` search queries (REST search API;
  works with or without a personal token).
- READMEs from raw.githubusercontent.com (no API quota used).
"""

from __future__ import annotations

import logging
import math
import re
from collections.abc import Iterable, Iterator
from datetime import date, timedelta

from atlas.collect.common import iso_date, new_record, pushed_cutoff, snapshot_date
from atlas.config import load_config
from atlas.http import CachedClient, github_headers

log = logging.getLogger(__name__)

API = "https://api.github.com"
_LINK_RE = re.compile(r"github\.com/([A-Za-z0-9](?:[A-Za-z0-9-]{0,38}))/([A-Za-z0-9_.-]{1,100})")
_RESERVED_OWNERS = {
    "about", "apps", "collections", "contact", "customer-stories", "enterprise", "events", "explore",
    "features", "login", "marketplace", "notifications", "orgs", "pricing", "pulls", "issues",
    "search", "security", "settings", "site", "sponsors", "topics", "trending", "users", "join",
    "readme", "github-copilot", "solutions", "resources", "team", "codespaces",
}


def _cfg() -> dict:
    return load_config("sources")


def search_client() -> CachedClient:
    c = _cfg()
    return CachedClient("github_search", headers=github_headers(),
                        min_interval=c["github"]["search"]["min_interval_seconds"],
                        max_retries=c["http"]["max_retries"], backoff_base=c["http"]["backoff_base_seconds"],
                        timeout=c["http"]["timeout_seconds"])


def code_search_client() -> CachedClient:
    c = _cfg()
    return CachedClient("github_code_search", headers=github_headers(),
                        min_interval=c["github"]["skill_files"]["min_interval_seconds"],
                        max_retries=c["http"]["max_retries"], backoff_base=c["http"]["backoff_base_seconds"],
                        timeout=c["http"]["timeout_seconds"])


def raw_client() -> CachedClient:
    c = _cfg()
    return CachedClient("github_raw", headers={"User-Agent": "ai-atlas-collector"},
                        min_interval=c["github_raw"]["min_interval_seconds"],
                        max_retries=c["http"]["max_retries"], backoff_base=c["http"]["backoff_base_seconds"],
                        timeout=c["http"]["timeout_seconds"])


# ----------------------------------------------------------------------------- normalization
def repo_record(item: dict, group: str) -> dict:
    lic = (item.get("license") or {}).get("spdx_id")
    return new_record(
        "gh:" + item["full_name"].lower(), source="github", group=group,
        full_name=item["full_name"], name=item["name"], url=item["html_url"],
        description=item.get("description"), stars=item.get("stargazers_count"),
        forks=item.get("forks_count"), created_at=iso_date(item.get("created_at")),
        pushed_at=iso_date(item.get("pushed_at")), license_spdx=lic, language=item.get("language"),
        topics=list(item.get("topics") or []), is_fork=bool(item.get("fork")),
        is_archived=bool(item.get("archived")),
    )


# ----------------------------------------------------------------------------- repository search
def _star_clause(lo: int, hi: int | None) -> str:
    return f"stars:>={lo}" if hi is None else f"stars:{lo}..{hi}"


def _search_page(client: CachedClient, q: str, page: int) -> dict:
    per_page = _cfg()["github"]["search"]["per_page"]
    r = client.get(f"{API}/search/repositories",
                   params={"q": q, "sort": "stars", "order": "desc", "per_page": per_page, "page": page})
    if r.status != 200:
        log.error("search failed (%d) for q=%r page=%d", r.status, q, page)
        return {"total_count": 0, "items": []}
    return r.json()


def _split(lo: int, hi: int | None, d0: date | None, d1: date | None):
    """Split a slice in two: by stars first, then by creation date. None if it cannot be split."""
    if hi is None:
        mid = max(lo * 2, lo + 10)
        return [(lo, mid - 1, d0, d1), (mid, None, d0, d1)]
    if hi > lo:
        mid = (lo + hi) // 2
        return [(lo, mid, d0, d1), (mid + 1, hi, d0, d1)]
    d0 = d0 or date.fromisoformat(_cfg()["github"]["search"]["created_from"])
    d1 = d1 or snapshot_date()
    if d1 > d0:
        mid = d0 + (d1 - d0) // 2
        return [(lo, hi, d0, mid), (lo, hi, mid + timedelta(days=1), d1)]
    return None


def search_repositories(client: CachedClient, base_query: str, min_stars: int) -> Iterator[dict]:
    """Yield every repository item matching `base_query`, slicing so each slice is <= the cap."""
    scfg = _cfg()["github"]["search"]
    cap, per_page = scfg["max_results_per_slice"], scfg["per_page"]
    stack = [(min_stars, None, None, None)]
    while stack:
        lo, hi, d0, d1 = stack.pop()
        q = f"{base_query} {_star_clause(lo, hi)}"
        if d0 and d1:
            q += f" created:{d0.isoformat()}..{d1.isoformat()}"
        first = _search_page(client, q, 1)
        total = first.get("total_count", 0)
        if total > cap:
            parts = _split(lo, hi, d0, d1)
            if parts:
                stack.extend(parts)
                continue
            log.warning("slice still has %d results and cannot be split: %s (truncated)", total, q)
        yield from first.get("items", [])
        for page in range(2, math.ceil(min(total, cap) / per_page) + 1):
            yield from _search_page(client, q, page).get("items", [])


def _freshness_clauses() -> list[str]:
    s = _cfg()["github"]["search"]
    cutoff = pushed_cutoff().isoformat()
    return [c.format(pushed_cutoff=cutoff) for c in s["freshness_clauses"]]


def _run_query_set(client: CachedClient, base: str, group: str, min_stars: int) -> list[dict]:
    extra = _cfg()["github"]["search"]["extra_qualifiers"]
    out = []
    for clause in _freshness_clauses():
        for item in search_repositories(client, f"{base} {clause} {extra}".strip(), min_stars):
            out.append(repo_record(item, group))
    return out


def collect_topics(client: CachedClient, limit: int | None = None) -> list[dict]:
    cfg = _cfg()
    out = []
    for topic in cfg["github"]["topics"][:limit]:
        recs = _run_query_set(client, f"topic:{topic}", f"topic:{topic}", cfg["filters"]["min_stars_default"])
        log.info("topic:%s -> %d repos", topic, len(recs))
        out += recs
    return out


def collect_keyword_groups(client: CachedClient, limit: int | None = None) -> list[dict]:
    cfg = _cfg()
    f = cfg["filters"]
    out = []
    for name, grp in list(cfg["github"]["keyword_groups"].items())[:limit]:
        min_stars = f["min_stars_niche"] if grp.get("niche") else f["min_stars_default"]
        for query in grp["queries"]:
            recs = _run_query_set(client, query, f"kw:{name}", min_stars)
            log.info("kw:%s %r -> %d repos", name, query, len(recs))
            out += recs
    return out


# ----------------------------------------------------------------------------- repos found by name
def collect_skill_file_repos(client: CachedClient, limit: int | None = None) -> set[str]:
    sk = _cfg()["github"]["skill_files"]
    names: set[str] = set()
    for size in sk["size_slices"][:limit]:
        q = f"{sk['code_search_query']} size:{size}"
        for page in range(1, sk["max_pages_per_slice"] + 1):
            r = client.get(f"{API}/search/code", params={"q": q, "per_page": 100, "page": page})
            if r.status != 200:
                log.error("code search failed (%d) for %r page %d", r.status, q, page)
                break
            items = r.json().get("items", [])
            names.update(i["repository"]["full_name"] for i in items)
            if len(items) < 100:
                break
    log.info("SKILL.md code search -> %d repos", len(names))
    return names


def parse_repo_links(markdown: str) -> set[str]:
    names = set()
    for owner, repo in _LINK_RE.findall(markdown):
        repo = re.sub(r"(\.git|[.\-_])+$", "", repo)
        if owner.lower() in _RESERVED_OWNERS or not repo:
            continue
        names.add(f"{owner}/{repo}")
    return names


def fetch_readme(client: CachedClient, full_name: str) -> str | None:
    base = _cfg()["github_raw"]["base_url"]
    for fname in _cfg()["github_raw"]["readme_candidates"]:
        r = client.get(f"{base}/{full_name}/HEAD/{fname}")
        if r.status == 200 and r.text.strip():
            return r.text
    return None


def collect_curated_links(raw: CachedClient, limit: int | None = None) -> dict[str, set[str]]:
    """Return {list_repo: {linked repos}}. The list repo itself is included as a candidate too."""
    out = {}
    for lst in _cfg()["github"]["curated_lists"][:limit]:
        text = fetch_readme(raw, lst) or ""
        links = {n for n in parse_repo_links(text) if n.lower() != lst.lower()}
        out[lst] = links
        log.info("curated %s -> %d linked repos", lst, len(links))
    return out


def _batches(names: Iterable[str], max_len: int = 240) -> Iterator[list[str]]:
    """Group names so that 'repo:a repo:b ... fork:true' stays under the search query length limit."""
    def qlen(b: list[str]) -> int:
        return len(" ".join(f"repo:{x}" for x in b)) + len(" fork:true")

    batch: list[str] = []
    for n in names:
        if batch and qlen(batch + [n]) > max_len:
            yield batch
            batch = []
        batch.append(n)
    if batch:
        yield batch


def lookup_repos(client: CachedClient, names: Iterable[str]) -> list[dict]:
    """Fetch metadata for known repo names via batched search queries."""
    out = []
    names = sorted(set(names), key=str.lower)
    for i, batch in enumerate(_batches(names)):
        q = " ".join(f"repo:{n}" for n in batch) + " fork:true"
        r = client.get(f"{API}/search/repositories", params={"q": q, "per_page": 100})
        if r.status == 200:
            for item in r.json().get("items", []):
                rec = repo_record(item, "lookup")
                rec["groups"] = set()   # provenance comes from the stub that requested the lookup
                out.append(rec)
        else:
            log.warning("lookup failed (%d) for batch %d", r.status, i)
        if i and i % 100 == 0:
            log.info("repo lookup: %d batches done, %d found", i, len(out))
    log.info("repo lookup: %d names -> %d found", len(names), len(out))
    return out
