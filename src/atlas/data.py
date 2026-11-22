"""Load the processed candidate snapshot.

data/processed/candidates.parquet          metadata of included projects (no README text)
data/processed/readmes/part-NNN.parquet    (id, readme_excerpt) shards — internal only, kept small
                                           enough for GitHub (< 50 MB per file)
"""

from __future__ import annotations

import pandas as pd

from atlas.paths import PROCESSED_DIR

CANDIDATES = PROCESSED_DIR / "candidates.parquet"
README_DIR = PROCESSED_DIR / "readmes"
README_SHARD_ROWS = 10000


def write_candidates(df: pd.DataFrame) -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["readme_excerpt"]).to_parquet(CANDIDATES, compression="zstd", index=False)
    README_DIR.mkdir(parents=True, exist_ok=True)
    for old in README_DIR.glob("part-*.parquet"):   # regenerate shards from scratch (derived files)
        old.unlink()
    rd = df[["id", "readme_excerpt"]].sort_values("id").reset_index(drop=True)
    for i, start in enumerate(range(0, len(rd), README_SHARD_ROWS)):
        rd.iloc[start:start + README_SHARD_ROWS].to_parquet(
            README_DIR / f"part-{i:03d}.parquet", compression="zstd", compression_level=19, index=False)


def load_candidates(with_readme: bool = False) -> pd.DataFrame:
    df = pd.read_parquet(CANDIDATES)
    if with_readme:
        parts = sorted(README_DIR.glob("part-*.parquet"))
        rd = pd.concat([pd.read_parquet(p) for p in parts], ignore_index=True)
        df = df.merge(rd, on="id", how="left")
    return df
