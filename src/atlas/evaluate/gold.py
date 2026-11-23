"""Gold-label storage: `gold_labels` table in data/atlas.db, mirrored to data/gold/gold_labels.csv.

The CSV is committed to git (the database is not), so labels are never lost and can be restored on
another machine:  python -m atlas.evaluate.gold sync
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from atlas import db
from atlas.data import load_candidates
from atlas.paths import DATA_DIR, DB_PATH
from atlas.schema import GoldLabel

GOLD_DIR = DATA_DIR / "gold"
LABELS_CSV = GOLD_DIR / "gold_labels.csv"
SAMPLE_CSV = GOLD_DIR / "gold_sample.csv"
COLUMNS = ["project_id", "annotator", "asset_type", "sector_primary", "field_primary",
           "fields_secondary", "notes", "labeled_at"]


def load_sample() -> pd.DataFrame:
    return pd.read_csv(SAMPLE_CSV)


def ensure_projects(db_path: Path, ids: list[str]) -> None:
    """Make sure the sampled projects exist in `projects` (gold_labels has a foreign key to it)."""
    with db.connect(db_path) as conn:
        have = {r[0] for r in conn.execute("SELECT id FROM projects")}
    missing = [i for i in ids if i not in have]
    if not missing:
        return
    df = load_candidates(with_readme=True)
    df = df[df["id"].isin(missing)]
    with db.connect(db_path) as conn:
        db.upsert_projects(conn, [candidate_to_row(r) for r in df.to_dict("records")])


def candidate_to_row(r: dict) -> dict:
    row = {c: r.get(c) for c in db.PROJECT_COLUMNS}
    for k in ("sources", "topics", "collect_groups"):
        row[k] = json.dumps(list(row[k]) if row[k] is not None else [])
    for k in ("is_fork", "is_archived", "has_readme", "included"):
        v = row[k]
        row[k] = None if v is None or (isinstance(v, float) and pd.isna(v)) else int(bool(v))
    for k in ("stars", "forks", "likes", "downloads", "readme_chars"):
        v = row[k]
        row[k] = None if v is None or pd.isna(v) else int(v)
    return {k: (None if isinstance(v, float) and pd.isna(v) else v) for k, v in row.items()}


def save_label(label: GoldLabel, db_path: Path = DB_PATH, csv_path: Path = LABELS_CSV) -> None:
    """Validate, upsert into gold_labels, then rewrite the CSV mirror."""
    row = label.model_dump(mode="json")
    row["fields_secondary"] = json.dumps(row["fields_secondary"])
    row["labeled_at"] = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with db.connect(db_path) as conn:
        conn.execute(
            f"INSERT INTO gold_labels ({', '.join(COLUMNS)}) VALUES ({', '.join(':' + c for c in COLUMNS)}) "
            "ON CONFLICT(project_id, annotator) DO UPDATE SET "
            + ", ".join(f"{c} = excluded.{c}" for c in COLUMNS[2:]), row)
    export_csv(db_path, csv_path)


def read_labels(db_path: Path = DB_PATH) -> pd.DataFrame:
    with db.connect(db_path) as conn:
        rows = [dict(r) for r in conn.execute(f"SELECT {', '.join(COLUMNS)} FROM gold_labels")]
    df = pd.DataFrame(rows, columns=COLUMNS)
    df["fields_secondary"] = df["fields_secondary"].map(lambda s: json.loads(s) if isinstance(s, str) else [])
    return df


def export_csv(db_path: Path = DB_PATH, csv_path: Path = LABELS_CSV) -> None:
    df = read_labels(db_path).sort_values(["annotator", "project_id"])
    df["fields_secondary"] = df["fields_secondary"].map(json.dumps)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(csv_path, index=False)


def import_csv(db_path: Path = DB_PATH, csv_path: Path = LABELS_CSV) -> int:
    """Load labels from the CSV mirror into the DB (used on a fresh machine). Returns rows imported."""
    if not csv_path.exists():
        return 0
    df = pd.read_csv(csv_path, dtype=str, keep_default_na=False)
    ensure_projects(db_path, df["project_id"].unique().tolist())
    with db.connect(db_path) as conn:
        for r in df.to_dict("records"):
            r = {k: (v or None) for k, v in r.items()}
            r["fields_secondary"] = r["fields_secondary"] or "[]"
            conn.execute(
                f"INSERT INTO gold_labels ({', '.join(COLUMNS)}) VALUES ({', '.join(':' + c for c in COLUMNS)}) "
                "ON CONFLICT(project_id, annotator) DO NOTHING", r)
    return len(df)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m atlas.evaluate.gold")
    ap.add_argument("command", choices=["sync", "status"])
    args = ap.parse_args(argv)
    db.init_db(DB_PATH)
    if args.command == "sync":
        n = import_csv()
        print(f"Imported {n} labels from {LABELS_CSV}")
    sample = load_sample()
    labels = read_labels()
    for ann, grp in labels.groupby("annotator"):
        print(f"  {ann}: {grp['project_id'].isin(sample['id']).sum()} / {len(sample)} labeled")
    if labels.empty:
        print(f"  no labels yet (0 / {len(sample)})")


if __name__ == "__main__":
    main()
