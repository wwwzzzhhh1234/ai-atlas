"""Stratified gold-standard sample (M2).

    python -m atlas.evaluate.sample_gold     # -> data/gold/gold_sample.csv (idempotent for a given seed + snapshot)

Strata: (1) sector keyword groups with fixed quotas, so small sectors appear; (2) the remaining V1 projects
by a rough, rule-based asset type. The rough type is only for sampling — it is never used as a label.
"""

from __future__ import annotations

import argparse

import pandas as pd

from atlas.config import load_config
from atlas.data import load_candidates
from atlas.paths import DATA_DIR

GOLD_DIR = DATA_DIR / "gold"
SAMPLE_PATH = GOLD_DIR / "gold_sample.csv"

_MCP = {"kw:mcp_servers", "mcp_registry", "topic:mcp", "topic:mcp-server", "topic:model-context-protocol"}
_SKILL = {"skill_file", "topic:agent-skills", "topic:claude-skills"}
_WORKFLOW = {"topic:n8n", "topic:dify"}
_GOV = {"topic:guardrails", "topic:ai-safety"}
_AGENT = {"topic:ai-agent", "topic:ai-agents", "topic:agentic-ai", "topic:crewai", "topic:autogen", "topic:langgraph"}


def rough_asset_type(pid: str, groups: list[str]) -> str:
    g = {"curated" if x.startswith("curated:") else x for x in groups}
    if pid.startswith("hf:spaces/"):
        return "space_app"
    if pid.startswith("hf:"):
        return "model"
    for name, keys in (("workflow", _WORKFLOW), ("governance", _GOV), ("mcp", _MCP),
                       ("skill", _SKILL | {"curated"}), ("agent", _AGENT)):
        if g & keys:
            return name
    return "other"


def sector_stratum(groups: list[str], quotas: dict) -> str | None:
    for key in quotas:  # config order = priority when a project is in several sector groups
        if key in groups:
            return key
    return None


def draw(df: pd.DataFrame, cfg: dict) -> pd.DataFrame:
    seed = cfg["seed"]
    df = df.copy()
    df["groups"] = df["collect_groups"].map(list)
    df["sector_stratum"] = df["groups"].map(lambda g: sector_stratum(g, cfg["sector_quota"]))
    df["rough_asset_type"] = [rough_asset_type(i, g) for i, g in zip(df["id"], df["groups"])]
    picks = []
    for key, n in cfg["sector_quota"].items():
        pool = df[df["sector_stratum"] == key]
        picks.append(pool.sample(n=min(n, len(pool)), random_state=seed).assign(stratum=key))
    rest = df[df["sector_stratum"].isna()]
    for key, n in cfg["asset_type_quota"].items():
        pool = rest[rest["rough_asset_type"] == key]
        picks.append(pool.sample(n=min(n, len(pool)), random_state=seed).assign(stratum=f"type:{key}"))
    sample = pd.concat(picks, ignore_index=True)
    overlap = (sample.groupby("stratum", group_keys=False)
               .apply(lambda s: s.sample(frac=cfg["overlap_size"] / len(sample), random_state=seed)))
    sample["overlap"] = sample["id"].isin(overlap["id"])
    sample = sample.sample(frac=1, random_state=seed).reset_index(drop=True)   # shuffled labeling order
    sample["order"] = range(1, len(sample) + 1)
    return sample[["order", "id", "name", "url", "stars", "likes", "stratum", "rough_asset_type", "overlap"]]


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(prog="python -m atlas.evaluate.sample_gold").parse_args(argv)
    cfg = load_config("gold")
    df = load_candidates()
    df = df[df["label_v1"]]
    sample = draw(df, cfg)
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    sample.to_csv(SAMPLE_PATH, index=False)
    print(f"Wrote {len(sample)} items ({int(sample['overlap'].sum())} overlap) to {SAMPLE_PATH}")
    print(sample["stratum"].value_counts().to_string())


if __name__ == "__main__":
    main()
