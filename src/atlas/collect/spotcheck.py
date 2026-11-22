"""Draw a reproducible random sample of included candidates for manual checking (M1 "Done when").

    python -m atlas.collect.spotcheck            # 20 rows, seed 42 -> docs/m1_spotcheck.md
    python -m atlas.collect.spotcheck --n 30 --seed 7

The reviewer fills the "Verdict" column: OK / JUNK (not an AI project, spam, empty) /
WRONG-MERGE (two different projects merged) / BAD-META (wrong stars, dates, license...).
"""

from __future__ import annotations

import argparse
import json

import pandas as pd

from atlas.data import load_candidates
from atlas.paths import ROOT

OUT = ROOT / "docs" / "m1_spotcheck.md"


def _cell(text, n: int = 90) -> str:
    s = "" if text is None or (isinstance(text, float) and pd.isna(text)) else \
        str(text).replace("|", "/").replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def render(sample: pd.DataFrame, seed: int) -> str:
    lines = [f"# M1 spot check — {len(sample)} random included rows (seed {seed})", "",
             "Verdict: OK · JUNK · WRONG-MERGE · BAD-META. Add a note for anything not OK.", "",
             "| # | id | stars / likes | sources | groups | description | README start | Verdict | Note |",
             "|---|---|---|---|---|---|---|---|---|"]
    for i, r in enumerate(sample.itertuples(), 1):
        pop = r.stars if pd.notna(r.stars) else (f"♥{int(r.likes)}" if pd.notna(r.likes) else "")
        pop = int(pop) if isinstance(pop, float) else pop
        lines.append(f"| {i} | [{r.id}]({r.url}) | {pop} | {', '.join(r.sources)} | "
                     f"{_cell(', '.join(r.collect_groups), 40)} | {_cell(r.description)} | "
                     f"{_cell(r.readme_excerpt, 120)} |  |  |")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m atlas.collect.spotcheck")
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args(argv)
    df = load_candidates(with_readme=True)
    for col in ("sources", "collect_groups"):
        df[col] = df[col].map(lambda v: list(v) if not isinstance(v, str) else json.loads(v))
    sample = df.sample(n=min(args.n, len(df)), random_state=args.seed)
    OUT.write_text(render(sample, args.seed), encoding="utf-8")
    print(f"Wrote {len(sample)} rows to {OUT}")


if __name__ == "__main__":
    main()
