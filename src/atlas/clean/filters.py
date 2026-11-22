"""Inclusion filters (spec Section 7). Each returns an exclusion reason, or None to keep."""

from __future__ import annotations

import re
from datetime import date
from functools import lru_cache

from atlas.collect.common import pushed_cutoff
from atlas.config import load_config

AI_SOURCE_GROUPS = ("topic:", "kw:", "skill_file", "mcp_registry", "hf_model", "hf_space")


def _f() -> dict:
    return load_config("sources")["filters"]


@lru_cache(maxsize=1)
def _ai_regex() -> re.Pattern:
    return re.compile(_f()["ai_keywords"], re.I)


def is_ai_related(rec: dict) -> bool:
    if any(g.startswith(AI_SOURCE_GROUPS) for g in rec["groups"]):
        return True
    text = " ".join([rec.get("name") or "", rec.get("description") or "", " ".join(rec.get("topics") or [])])
    return bool(_ai_regex().search(text.replace("-", " ").replace("_", " ")))


def min_stars_for(rec: dict) -> int:
    """Lowest star threshold among the groups that found this record."""
    f = _f()
    niche_groups = {f"kw:{k}" for k, g in load_config("sources")["github"]["keyword_groups"].items()
                    if g.get("niche")}
    thresholds = [f["min_stars_default"]]
    for g in rec["groups"]:
        if g in niche_groups:
            thresholds.append(f["min_stars_niche"])
        elif g.startswith("curated"):
            thresholds.append(f["min_stars_by_group"]["curated"])
        elif g in f["min_stars_by_group"]:
            thresholds.append(f["min_stars_by_group"][g])
    return min(thresholds)


def is_fresh(rec: dict) -> bool:
    fr = _f()["freshness"]
    created, pushed = rec.get("created_at"), rec.get("pushed_at")
    if created and date.fromisoformat(created) >= date.fromisoformat(str(fr["created_on_or_after"])):
        return True
    return bool(pushed and date.fromisoformat(pushed) >= pushed_cutoff())


def metadata_exclusion(rec: dict) -> str | None:
    """Checks that need no README (run before fetching READMEs to save requests)."""
    f = _f()
    if rec["id"].startswith("gh:") and rec.get("stars") is None:
        return "metadata_not_found"
    if not is_ai_related(rec):
        return "not_ai_related"
    if f["exclude_forks"] and rec.get("is_fork"):
        return "fork"
    if f["exclude_archived"] and rec.get("is_archived"):
        return "archived"
    if not is_fresh(rec):
        return "stale"
    if rec.get("stars") is not None and rec["stars"] < min_stars_for(rec):
        return "low_stars"
    return None


def readme_exclusion(rec: dict) -> str | None:
    if not rec.get("has_readme"):
        return "no_readme"
    if (rec.get("readme_chars") or 0) < _f()["min_readme_chars"]:
        return "short_readme"
    return None
