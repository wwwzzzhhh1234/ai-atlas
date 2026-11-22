"""Shared helpers for collectors: the raw candidate record and date utilities.

A *record* is a plain dict with the `projects` columns plus `groups` (a set of provenance tags such
as "topic:llm", "kw:healthcare", "skill_file", "curated", "mcp_registry", "hf_model", "hf_space").
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from atlas.config import load_config

RECORD_FIELDS = (
    "id", "name", "url", "description", "stars", "forks", "likes", "downloads",
    "created_at", "pushed_at", "license_spdx", "language", "topics",
    "is_fork", "is_archived", "has_readme", "readme_excerpt", "readme_chars",
)


def new_record(id: str, *, source: str, group: str, **fields: Any) -> dict:
    rec: dict[str, Any] = {k: None for k in RECORD_FIELDS}
    rec.update(id=id, sources={source}, groups={group}, topics=[], full_name=None, raw_readme_url=None)
    rec.update(fields)
    return rec


def iso_date(value: str | None) -> str | None:
    return value[:10] if value else None


def snapshot_date() -> date:
    """Fixed collection date from config — keeps query strings (and cache keys) stable across re-runs."""
    return date.fromisoformat(str(load_config("sources")["snapshot_date"]))


def pushed_cutoff() -> date:
    months = load_config("sources")["filters"]["freshness"]["or_pushed_within_months"]
    return snapshot_date() - timedelta(days=round(months * 30.44))
