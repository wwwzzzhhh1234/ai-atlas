"""Selection of the V1 labeling set (tiered star thresholds, config/models.yaml -> v1_label_set)."""

from __future__ import annotations

from atlas.config import load_config


def niche_groups() -> set[str]:
    groups = load_config("sources")["github"]["keyword_groups"]
    return {f"kw:{name}" for name, g in groups.items() if g.get("niche")}


def in_v1_label_set(stars: int | None, likes: int | None, groups: list[str] | set[str]) -> bool:
    cfg = load_config("models")["v1_label_set"]
    if stars is None:
        return likes is not None and likes >= cfg["hf_min_likes"]
    if stars >= cfg["min_stars_general"]:
        return True
    return stars >= cfg["min_stars_niche"] and bool(set(groups) & niche_groups())
