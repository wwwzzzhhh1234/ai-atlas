"""Files read by pip / tools with the Windows locale encoding (e.g. GBK) must be pure ASCII."""
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("name", ["requirements.txt", "requirements-ml.txt", "pyproject.toml", ".env.example"])
def test_ascii_only(name):
    data = (ROOT / name).read_bytes()
    bad = [i for i, b in enumerate(data) if b > 127]
    assert not bad, f"{name} has non-ASCII bytes at {bad[:5]} (breaks pip on Chinese Windows)"
