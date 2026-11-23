"""Inter-annotator agreement on the gold set (Cohen's kappa).

    python -m atlas.evaluate.agreement      # -> docs/gold_agreement.md

Uses every project labeled by exactly the two annotators being compared (default: the two with the most
labels). Reports kappa and raw agreement for asset type, primary sector and primary field.
"""

from __future__ import annotations

import argparse

import pandas as pd
from sklearn.metrics import cohen_kappa_score

from atlas.evaluate.gold import read_labels
from atlas.paths import ROOT

OUT = ROOT / "docs" / "gold_agreement.md"
TARGETS = ("asset_type", "sector_primary", "field_primary")


def agreement(labels: pd.DataFrame, a: str, b: str) -> tuple[int, dict[str, tuple[float, float]]]:
    la = labels[labels["annotator"] == a].set_index("project_id")
    lb = labels[labels["annotator"] == b].set_index("project_id")
    both = la.index.intersection(lb.index)
    res = {}
    for col in TARGETS:
        x, y = la.loc[both, col], lb.loc[both, col]
        kappa = cohen_kappa_score(x, y) if len(both) and (x.nunique() > 1 or y.nunique() > 1) else float("nan")
        res[col] = (kappa, float((x == y).mean()) if len(both) else float("nan"))
    return len(both), res


def render(labels: pd.DataFrame) -> str:
    counts = labels["annotator"].value_counts()
    lines = ["# Gold set — inter-annotator agreement", "",
             "Labels per annotator: " + (", ".join(f"{a}: {n}" for a, n in counts.items()) or "none")]
    if len(counts) < 2:
        lines += ["", "**Pending:** no second annotator yet (spec M2 allows this; kappa is computed once "
                  "annotator 2 labels the overlap subset)."]
        return "\n".join(lines) + "\n"
    a, b = counts.index[:2]
    n, res = agreement(labels, a, b)
    lines += ["", f"Compared **{a}** vs **{b}** on **{n}** shared items.", "",
              "| Target | Cohen's kappa | Raw agreement |", "|---|---:|---:|"]
    lines += [f"| {t} | {k:.3f} | {p:.1%} |" for t, (k, p) in res.items()]
    lines += ["", "Reading guide (Landis & Koch): 0.41–0.60 moderate · 0.61–0.80 substantial · > 0.80 almost perfect."]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    argparse.ArgumentParser(prog="python -m atlas.evaluate.agreement").parse_args(argv)
    text = render(read_labels())
    OUT.write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
