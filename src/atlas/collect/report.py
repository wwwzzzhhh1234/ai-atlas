"""Collection report: counts by source, by provenance group, exclusion reasons, star histogram.

    python -m atlas.collect.report     # rebuild the report from data/atlas.db
"""

from __future__ import annotations

import json
from collections import Counter

from atlas.paths import DB_PATH, ROOT

REPORT_PATH = ROOT / "reports" / "collection_report.md"
STAR_BUCKETS = [(0, 19), (20, 49), (50, 99), (100, 199), (200, 499), (500, 999), (1000, 4999),
                (5000, 19999), (20000, None)]


def _table(counter: Counter, header: tuple[str, str]) -> str:
    lines = [f"| {header[0]} | {header[1]} |", "|---|---:|"]
    lines += [f"| {k} | {v:,} |" for k, v in counter.most_common()]
    return "\n".join(lines)


def _group_key(g: str) -> str:
    return "curated" if g.startswith("curated:") else g


def summarize(rows: list[dict]) -> dict:
    inc = [r for r in rows if r["included"]]
    src_all, src_inc, grp_inc, grp_all = Counter(), Counter(), Counter(), Counter()
    for r in rows:
        srcs = json.loads(r["sources"]) if isinstance(r["sources"], str) else r["sources"]
        groups = json.loads(r["collect_groups"]) if isinstance(r["collect_groups"], str) else r["collect_groups"]
        for s in srcs:
            src_all[s] += 1
            src_inc[s] += bool(r["included"])
        for g in {_group_key(g) for g in groups}:
            grp_all[g] += 1
            grp_inc[g] += bool(r["included"])
    stars = Counter()
    for r in inc:
        if r["stars"] is None:
            stars["n/a (HF / registry-only)"] += 1
            continue
        for lo, hi in STAR_BUCKETS:
            if r["stars"] >= lo and (hi is None or r["stars"] <= hi):
                stars[f"{lo:,}+" if hi is None else f"{lo:,}–{hi:,}"] += 1
    return {"total": len(rows), "included": len(inc), "src_all": src_all, "src_inc": src_inc,
            "grp_all": grp_all, "grp_inc": grp_inc, "stars": stars,
            "reasons": Counter(r["exclude_reason"] for r in rows if not r["included"]),
            "multi_source": sum(1 for r in inc if len(json.loads(r["sources"])) > 1)}


def render(s: dict, stats=None, elapsed: float | None = None) -> str:
    out = ["# Collection report", "",
           f"- Unique projects collected: **{s['total']:,}**",
           f"- Included (pass all filters): **{s['included']:,}**",
           f"- Included projects found by more than one source: {s['multi_source']:,}"]
    if stats is not None:
        out.append(f"- HTTP: {stats.network_calls:,} network calls, {stats.cache_hits:,} cache hits, "
                   f"{stats.errors:,} errors" + (f", {elapsed / 60:.1f} min" if elapsed else ""))
    src = Counter({k: f"{s['src_inc'][k]:,} / {v:,}" for k, v in s["src_all"].items()})
    grp_lines = ["| Group | Included / collected |", "|---|---:|"] + [
        f"| {g} | {s['grp_inc'][g]:,} / {n:,} |" for g, n in s["grp_all"].most_common()]
    order = [f"{lo:,}+" if hi is None else f"{lo:,}–{hi:,}" for lo, hi in STAR_BUCKETS]
    star_lines = ["| Stars | Included |", "|---|---:|"] + [
        f"| {b} | {s['stars'][b]:,} |" for b in order + ["n/a (HF / registry-only)"] if s["stars"][b]]
    out += ["", "## By source (included / collected)", "",
            "| Source | Included / collected |", "|---|---:|"]
    out += [f"| {k} | {v} |" for k, v in sorted(src.items())]
    out += ["", "## By provenance group", "", *grp_lines,
            "", "## Exclusion reasons", "", _table(s["reasons"], ("Reason", "Count")),
            "", "## Stars histogram (included GitHub projects)", "", *star_lines, ""]
    return "\n".join(out)


def write_report(rows: list[dict], stats=None, elapsed: float | None = None) -> str:
    text = render(summarize(rows), stats, elapsed)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(text, encoding="utf-8")
    return text


if __name__ == "__main__":
    from atlas import db
    with db.connect(DB_PATH) as conn:
        rows = [dict(r) for r in conn.execute("SELECT * FROM projects")]
    print(write_report(rows))
