"""Run the full collection pipeline (M1).

    python -m atlas.collect.run                 # everything
    python -m atlas.collect.run --only github   # one source (github | mcp | hf)
    python -m atlas.collect.run --smoke         # tiny run for testing (first topic / group / page)

Resumable and idempotent: every HTTP response is cached under data/cache/http/, so an interrupted
run continues where it stopped and a repeated run makes no new API calls for cached items.
Outputs: projects table in data/atlas.db, data/processed/candidates.parquet (included rows),
reports/collection_report.md.
"""

from __future__ import annotations

import argparse
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from dotenv import load_dotenv

from atlas import db
from atlas.clean.dedup import merge
from atlas.clean.filters import metadata_exclusion, readme_exclusion
from atlas.clean.readme import clean_readme
from atlas.collect import github, huggingface, mcp_registry
from atlas.collect.common import new_record
from atlas.config import load_config
from atlas.data import write_candidates
from atlas.http import STATS
from atlas.paths import DB_PATH, RAW_DIR
from atlas.schema import Project
from atlas.select import in_v1_label_set

log = logging.getLogger("atlas.collect")


# ----------------------------------------------------------------------------- gather
def gather_github(smoke: bool) -> list[dict]:
    lim = 1 if smoke else None
    search, code, raw = github.search_client(), github.code_search_client(), github.raw_client()
    records = github.collect_topics(search, limit=lim) + github.collect_keyword_groups(search, limit=lim)

    stubs = [new_record("gh:" + n.lower(), source="github", group="skill_file", full_name=n)
             for n in github.collect_skill_file_repos(code, limit=lim)]
    for lst, links in github.collect_curated_links(raw, limit=lim).items():
        stubs.append(new_record("gh:" + lst.lower(), source="github", group=f"curated:{lst}", full_name=lst))
        stubs += [new_record("gh:" + n.lower(), source="github", group=f"curated:{lst}", full_name=n)
                  for n in links]
    return records + stubs


def fill_missing_metadata(records: list[dict]) -> list[dict]:
    """Look up GitHub metadata for stubs (from SKILL.md search, curated lists, MCP registry)."""
    have = {r["id"] for r in records if r.get("stars") is not None}
    lookup_registry = load_config("sources")["mcp_registry"].get("lookup_repos", True)
    groups_by_id: dict[str, set] = {}
    for r in records:
        groups_by_id.setdefault(r["id"], set()).update(r["groups"])
    need = {r["full_name"] for r in records
            if r["id"].startswith("gh:") and r["id"] not in have and r.get("full_name")
            and (lookup_registry or groups_by_id[r["id"]] != {"mcp_registry"})}
    log.info("GitHub metadata lookup for %d repos found by name", len(need))
    return records + github.lookup_repos(github.search_client(), need) if need else records


# ----------------------------------------------------------------------------- readmes
def attach_readmes(records: dict[str, dict]) -> None:
    max_chars = load_config("sources")["filters"]["readme_excerpt_max_chars"]
    todo = [r for r in records.values() if r["exclude_reason"] is None and r["id"].split(":")[0] in ("gh", "hf")]
    raw, hf = github.raw_client(), huggingface.client()

    def work(rec: dict) -> None:
        text = (github.fetch_readme(raw, rec["full_name"]) if rec["id"].startswith("gh:")
                else huggingface.fetch_readme(hf, rec))
        cleaned = clean_readme(text, max_chars=max_chars)
        rec["has_readme"] = text is not None
        rec["readme_excerpt"] = cleaned or None
        rec["readme_chars"] = len(cleaned)
        if rec.get("hf_header"):   # HF Space: stitch metadata + README body (decision 2026-11-22)
            rec["readme_excerpt"] = (rec["hf_header"] + ("\n\n" + cleaned if cleaned else "")).strip()
            rec["informative_chars"] = len(rec.get("hf_informative") or "") + len(cleaned)

    log.info("Fetching READMEs for %d records", len(todo))
    with ThreadPoolExecutor(max_workers=8) as pool:
        for i, _ in enumerate(pool.map(work, todo), 1):
            if i % 1000 == 0:
                log.info("  READMEs: %d / %d", i, len(todo))


# ----------------------------------------------------------------------------- outputs
def to_row(rec: dict, collected_at: str) -> dict:
    """Validate with pydantic, then encode for SQLite."""
    p = Project(
        id=rec["id"], name=rec.get("name") or rec.get("full_name") or rec["id"].split(":", 1)[1],
        url=rec.get("url"), description=rec.get("description"), sources=sorted(rec["sources"]),
        stars=rec.get("stars"), forks=rec.get("forks"), likes=rec.get("likes"), downloads=rec.get("downloads"),
        created_at=rec.get("created_at"), pushed_at=rec.get("pushed_at"), license_spdx=rec.get("license_spdx"),
        language=rec.get("language"), topics=rec.get("topics") or [], is_fork=rec.get("is_fork"),
        is_archived=rec.get("is_archived"), has_readme=rec.get("has_readme"),
        readme_excerpt=rec.get("readme_excerpt"), readme_chars=rec.get("readme_chars"),
        collect_groups=sorted(rec["groups"]), included=rec["exclude_reason"] is None,
        exclude_reason=rec["exclude_reason"], collected_at=collected_at,
    )
    row = p.model_dump(mode="json")
    for k in ("sources", "topics", "collect_groups"):
        row[k] = json.dumps(row[k])
    for k in ("is_fork", "is_archived", "has_readme", "included"):
        row[k] = None if row[k] is None else int(row[k])
    return row


def write_outputs(records: dict[str, dict]) -> list[dict]:
    import pandas as pd

    collected_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = [to_row(r, collected_at) for r in records.values()]
    db.init_db(DB_PATH)
    with db.connect(DB_PATH) as conn:
        db.upsert_projects(conn, rows)
    df = pd.DataFrame([r for r in rows if r["included"]])
    for k in ("sources", "topics", "collect_groups"):
        if k in df:
            df[k] = df[k].map(json.loads)
    df["label_v1"] = [in_v1_label_set(None if pd.isna(st) else st, None if pd.isna(lk) else lk, g)
                      for st, lk, g in zip(df["stars"], df["likes"], df["collect_groups"])]
    write_candidates(df)
    log.info("Wrote %d projects to DB, %d included rows to candidates.parquet (%d in V1 label set)",
             len(rows), len(df), int(df["label_v1"].sum()))
    return rows


# ----------------------------------------------------------------------------- main
def setup_logging() -> None:
    logdir = RAW_DIR / "logs"
    logdir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(logdir / f"collect_{stamp}.log",
                                                                               encoding="utf-8")])
    logging.getLogger("httpx").setLevel(logging.WARNING)


def run(only: set[str], smoke: bool) -> list[dict]:
    t0 = time.time()
    records: list[dict] = []
    if "github" in only:
        records += gather_github(smoke)
    if "mcp" in only:
        records += mcp_registry.collect(mcp_registry.client(), max_pages=1 if smoke else None)
    if "hf" in only:
        records += huggingface.collect(huggingface.client()) if not smoke else \
            huggingface.collect_kind(huggingface.client(), "spaces")[:20]
    if "github" in only or "mcp" in only:
        records = fill_missing_metadata(records)

    merged = merge(records)
    for rec in merged.values():
        rec["exclude_reason"] = metadata_exclusion(rec)
    attach_readmes(merged)
    for rec in merged.values():
        if rec["exclude_reason"] is None:
            rec["exclude_reason"] = readme_exclusion(rec)

    rows = write_outputs(merged)
    from atlas.collect.report import write_report
    write_report(rows, STATS, elapsed=time.time() - t0)
    log.info("HTTP: %d network calls, %d cache hits, %d errors (%.0fs)",
             STATS.network_calls, STATS.cache_hits, STATS.errors, time.time() - t0)
    return rows


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m atlas.collect.run")
    ap.add_argument("--only", default="github,mcp,hf", help="comma list of: github, mcp, hf")
    ap.add_argument("--smoke", action="store_true", help="tiny run to test the pipeline")
    args = ap.parse_args(argv)
    load_dotenv()
    setup_logging()
    run(set(args.only.split(",")), args.smoke)


if __name__ == "__main__":
    main()
