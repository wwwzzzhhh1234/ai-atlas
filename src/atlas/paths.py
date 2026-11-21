"""Project paths. Override the root with the ATLAS_ROOT environment variable."""

from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    env = os.environ.get("ATLAS_ROOT")
    if env:
        return Path(env).resolve()
    # src/atlas/paths.py -> project root is two levels above `src`
    return Path(__file__).resolve().parents[2]


ROOT = project_root()
CONFIG_DIR = ROOT / "config"
DATA_DIR = ROOT / "data"
DB_PATH = DATA_DIR / "atlas.db"
CACHE_DIR = DATA_DIR / "cache"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
REVIEW_DIR = DATA_DIR / "review"
