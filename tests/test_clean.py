from atlas.clean.dedup import merge
from atlas.clean.readme import clean_readme
from atlas.collect.common import new_record


def test_clean_readme_strips_noise():
    raw = """---
title: x
---
<!-- hidden -->
[![CI](https://img.shields.io/x.svg)](https://ci) ![logo](logo.png)
# My Tool
<p align="center">An <b>AI</b> agent &amp; helper. See [docs](https://docs.example.com).</p>

```bash
pip install tool
```
| a | b |
|---|---|
"""
    out = clean_readme(raw)
    assert "My Tool" in out and "An AI agent & helper. See docs." in out
    for junk in ("shields", "logo.png", "hidden", "title: x", "<p", "https://", "pip install", "|---"):
        assert junk not in out


def test_clean_readme_truncates_on_word_boundary():
    out = clean_readme("word " * 5000, max_chars=100)
    assert len(out) <= 102 and out.endswith("…")


def test_clean_readme_empty():
    assert clean_readme(None) == "" and clean_readme("") == ""


def test_merge_unions_sources_and_prefers_metadata():
    stub = new_record("gh:a/b", source="mcp_registry", group="mcp_registry", full_name="a/b")
    meta = new_record("gh:a/b", source="github", group="topic:llm", name="b", stars=150, full_name="A/b")
    other = new_record("gh:c/d", source="github", group="kw:startup", name="d", stars=30)
    out = merge([stub, meta, other])
    assert set(out) == {"gh:a/b", "gh:c/d"}
    ab = out["gh:a/b"]
    assert ab["sources"] == {"github", "mcp_registry"}
    assert ab["groups"] == {"topic:llm", "mcp_registry"}
    assert ab["stars"] == 150 and ab["full_name"] == "A/b"


def test_hf_space_boilerplate_removed():
    assert clean_readme("---\nsdk: gradio\n---\n\nCheck out the configuration reference at https://huggingface.co/docs/hub/spaces-config-reference\n") == ""


def test_candidates_roundtrip(tmp_path, monkeypatch):
    import pandas as pd
    from atlas import data
    monkeypatch.setattr(data, "PROCESSED_DIR", tmp_path)
    monkeypatch.setattr(data, "CANDIDATES", tmp_path / "candidates.parquet")
    monkeypatch.setattr(data, "README_DIR", tmp_path / "readmes")
    monkeypatch.setattr(data, "README_SHARD_ROWS", 2)
    df = pd.DataFrame({"id": ["gh:a/b", "gh:c/d", "gh:e/f"], "name": ["b", "d", "f"],
                       "readme_excerpt": ["x" * 300, "y" * 300, "z" * 300]})
    data.write_candidates(df)
    assert len(list((tmp_path / "readmes").glob("part-*.parquet"))) == 2
    assert "readme_excerpt" not in data.load_candidates().columns
    full = data.load_candidates(with_readme=True)
    assert full.set_index("id").loc["gh:c/d", "readme_excerpt"] == "y" * 300
