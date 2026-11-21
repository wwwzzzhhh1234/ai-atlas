"""Load YAML configuration files from config/."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from atlas.paths import CONFIG_DIR


def load_yaml(path: Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a YAML mapping at the top level")
    return data


@lru_cache(maxsize=None)
def load_config(name: str) -> dict[str, Any]:
    """Load config/<name>.yaml (e.g. 'models', 'sources')."""
    return load_yaml(CONFIG_DIR / f"{name}.yaml")
