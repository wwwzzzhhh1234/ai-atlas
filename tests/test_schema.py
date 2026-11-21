from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from atlas.schema import GoldLabel, Label, LabelOutput, Project, Related

NOW = datetime(2026, 11, 21, tzinfo=timezone.utc)


def test_valid_label_output(valid_label_output):
    out = LabelOutput(**valid_label_output)
    assert out.inputs == ["text", "api"]  # normalized to lowercase


@pytest.mark.parametrize("patch", [
    {"field_primary": "S01.1"},                       # field not in sector S03
    {"sector_primary": "S99"},                        # unknown sector
    {"fields_secondary": ["S03.1"]},                  # repeats primary
    {"fields_secondary": ["S01.1", "S02.1", "S04.1", "S06.1"]},  # > 3
    {"fields_secondary": ["OTHER"]},
    {"asset_type": "plugin"},
    {"non_tech_usability": 6},
    {"deploy_difficulty": 0},
    {"confidence": 1.2},
    {"use_cases": ["only one"]},
    {"business_summary": "word " * 61},
    {"inputs": ["PDF file!"]},
    {"unexpected_key": 1},
])
def test_invalid_label_output(valid_label_output, patch):
    with pytest.raises(ValidationError):
        LabelOutput(**{**valid_label_output, **patch})


def test_other_is_allowed(valid_label_output):
    LabelOutput(**{**valid_label_output, "sector_primary": "OTHER", "field_primary": "OTHER",
                   "fields_secondary": []})


def test_label_row(valid_label_output):
    row = Label(**valid_label_output, project_id="gh:acme/crm-mcp", model="gemini-4-neon",
                prompt_version="label_v1", cost_usd=0.02, labeled_at=NOW)
    assert row.status == "ok"


def test_project_ids():
    base = dict(name="x", sources=["github"], collected_at=NOW)
    Project(id="gh:owner/repo", **base)
    Project(id="hf:Org/Model", **base)          # hf ids keep case
    Project(id="mcp:io.github.acme/server", **base)
    for bad in ["gh:Owner/Repo", "owner/repo", "gh:", "gl:owner/repo"]:
        with pytest.raises(ValidationError):
            Project(id=bad, **base)


def test_project_sources_deduped_and_required():
    p = Project(id="gh:a/b", name="b", sources=["github", "mcp_registry", "github"], collected_at=NOW)
    assert [s.value for s in p.sources] == ["github", "mcp_registry"]
    with pytest.raises(ValidationError):
        Project(id="gh:a/b", name="b", sources=[], collected_at=NOW)


def test_gold_label():
    GoldLabel(project_id="gh:a/b", annotator="zw", asset_type="app",
              sector_primary="S09", field_primary="S09.2")
    with pytest.raises(ValidationError):
        GoldLabel(project_id="gh:a/b", annotator="zw", asset_type="app",
                  sector_primary="S09", field_primary="S10.2")


def test_related():
    Related(project_id="gh:a/b", related_id="gh:c/d", kind="complement", score=0.7)
    with pytest.raises(ValidationError):
        Related(project_id="gh:a/b", related_id="gh:a/b", kind="alternative", score=1.0)
    with pytest.raises(ValidationError):
        Related(project_id="gh:a/b", related_id="gh:c/d", kind="similar", score=1.0)
