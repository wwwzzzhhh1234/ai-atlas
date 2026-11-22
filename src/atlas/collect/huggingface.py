"""Hugging Face collector (spec Section 7, source 3): top models and Spaces by likes.

Uses the public Hub REST API (the same endpoints `huggingface_hub` calls) through our cached client,
so every page and model card is cached like the other sources.
Ids: models -> `hf:owner/name`, Spaces -> `hf:spaces/owner/name` (models and Spaces can share a name).
"""

from __future__ import annotations

import logging
import re

from atlas.collect.common import iso_date, new_record
from atlas.config import load_config
from atlas.http import CachedClient

log = logging.getLogger(__name__)
_NEXT_RE = re.compile(r'<([^>]+)>;\s*rel="next"')
_SPDX = {"mit": "MIT", "apache-2.0": "Apache-2.0", "bsd-3-clause": "BSD-3-Clause", "gpl-3.0": "GPL-3.0",
         "agpl-3.0": "AGPL-3.0", "cc-by-4.0": "CC-BY-4.0", "cc-by-sa-4.0": "CC-BY-SA-4.0",
         "cc-by-nc-4.0": "CC-BY-NC-4.0", "openrail": "OpenRAIL", "llama3": "Llama-3", "gemma": "Gemma"}
_NOISE_TAG = re.compile(r"^(region:|deploy:|endpoints_compatible|autotrain_compatible|text-generation-inference"
                        r"|safetensors|eval-results|custom_code|has_space)")
_EXPAND = {"models": ["likes", "downloads", "createdAt", "lastModified", "tags", "pipeline_tag",
                      "cardData", "library_name"],
           "spaces": ["likes", "createdAt", "lastModified", "tags", "sdk", "cardData"]}


def client() -> CachedClient:
    c = load_config("sources")
    # 401/403 on a gated model card is a definitive answer: cache it, do not retry.
    cl = CachedClient("huggingface", headers={"User-Agent": "ai-atlas-collector"},
                      min_interval=c["huggingface"]["min_interval_seconds"],
                      max_retries=c["http"]["max_retries"], backoff_base=c["http"]["backoff_base_seconds"],
                      timeout=c["http"]["timeout_seconds"])
    cl.cacheable = {200, 401, 403, 404}
    cl.retryable = {429, 500, 502, 503, 504}
    return cl


def _license(card: dict) -> str | None:
    lic = card.get("license")
    if isinstance(lic, list):
        lic = lic[0] if lic else None
    if not lic:
        return None
    return _SPDX.get(str(lic).lower(), str(lic))


def item_record(item: dict, kind: str) -> dict:
    card = item.get("cardData") or {}
    hid = item["id"]
    is_space = kind == "spaces"
    tags = [t for t in item.get("tags") or [] if not _NOISE_TAG.match(t)]
    if item.get("pipeline_tag") and item["pipeline_tag"] not in tags:
        tags.insert(0, item["pipeline_tag"])
    return new_record(
        ("hf:spaces/" if is_space else "hf:") + hid, source="huggingface",
        group="hf_space" if is_space else "hf_model",
        name=card.get("title") or hid.split("/")[-1],
        url=f"https://huggingface.co/{'spaces/' if is_space else ''}{hid}",
        description=card.get("short_description"), likes=item.get("likes"),
        downloads=item.get("downloads"), created_at=iso_date(item.get("createdAt")),
        pushed_at=iso_date(item.get("lastModified")), license_spdx=_license(card),
        language=None, topics=tags[:20], is_fork=False, is_archived=False,
        raw_readme_url=f"https://huggingface.co/{'spaces/' if is_space else ''}{hid}/raw/main/README.md",
    )


def collect_kind(c: CachedClient, kind: str) -> list[dict]:
    cfg = load_config("sources")["huggingface"]
    max_items = cfg[f"max_{kind}"]
    params = {"sort": cfg["sort_by"], "direction": -1, "limit": cfg["page_size"], "expand[]": _EXPAND[kind]}
    url: str | None = f"{cfg['api_base']}/api/{kind}"
    out: list[dict] = []
    while url and len(out) < max_items:
        r = c.get(url, params=params)
        params = None  # the "next" link already carries every parameter
        if r.status != 200:
            log.error("HF %s page failed (%d)", kind, r.status)
            break
        items = r.json()
        for it in items:
            if (it.get("likes") or 0) < cfg["min_likes"]:
                url = None
                break
            out.append(item_record(it, kind))
        else:
            m = _NEXT_RE.search(r.headers.get("link", ""))
            url = m.group(1) if m and items else None
    log.info("Hugging Face %s -> %d items", kind, len(out[:max_items]))
    return out[:max_items]


def collect(c: CachedClient) -> list[dict]:
    return collect_kind(c, "models") + collect_kind(c, "spaces")


def fetch_readme(c: CachedClient, rec: dict) -> str | None:
    r = c.get(rec["raw_readme_url"])
    return r.text if r.status == 200 and r.text.strip() else None
