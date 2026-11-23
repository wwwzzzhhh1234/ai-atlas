import json

import pandas as pd
import pytest

from atlas import db
from atlas.evaluate import agreement, gold, sample_gold
from atlas.schema import GoldLabel


def test_rough_asset_type():
    f = sample_gold.rough_asset_type
    assert f("hf:spaces/a/b", ["hf_space"]) == "space_app"
    assert f("hf:a/b", ["hf_model"]) == "model"
    assert f("gh:a/b", ["kw:mcp_servers", "topic:llm"]) == "mcp"
    assert f("gh:a/b", ["topic:n8n", "topic:mcp"]) == "workflow"
    assert f("gh:a/b", ["curated:x/y"]) == "skill"
    assert f("gh:a/b", ["topic:llm"]) == "other"


def test_draw_respects_quotas_and_overlap():
    rows = []
    for i in range(400):
        groups = ["kw:healthcare"] if i < 50 else (["kw:mcp_servers"] if i < 250 else ["topic:llm"])
        rows.append({"id": f"gh:o/r{i}", "name": f"r{i}", "url": "u", "stars": 100, "likes": None,
                     "collect_groups": groups})
    cfg = {"seed": 1, "sector_quota": {"kw:healthcare": 20, "kw:startup": 20},
           "asset_type_quota": {"mcp": 25, "other": 15}, "overlap_size": 12}
    s = sample_gold.draw(pd.DataFrame(rows), cfg)
    assert s["stratum"].value_counts().to_dict() == {"type:mcp": 25, "kw:healthcare": 20, "type:other": 15}
    assert s["id"].is_unique and list(s["order"]) == list(range(1, 61))
    assert 10 <= s["overlap"].sum() <= 14
    assert s.equals(sample_gold.draw(pd.DataFrame(rows), cfg))   # reproducible


@pytest.fixture
def gold_db(tmp_path):
    path = db.init_db(tmp_path / "a.db")
    row = {c: None for c in db.PROJECT_COLUMNS}
    with db.connect(path) as conn:
        for pid in ("gh:a/b", "gh:c/d"):
            db.upsert_projects(conn, [{**row, "id": pid, "name": pid, "sources": "[]", "topics": "[]",
                                       "collect_groups": "[]", "included": 1, "collected_at": "t"}])
    return path


def test_save_label_upserts_and_mirrors_csv(gold_db, tmp_path):
    csv = tmp_path / "gold.csv"
    lab = GoldLabel(project_id="gh:a/b", annotator="zw", asset_type="mcp", sector_primary="S01",
                    field_primary="S01.2", fields_secondary=["S06.2"])
    gold.save_label(lab, gold_db, csv)
    gold.save_label(lab.model_copy(update={"field_primary": "S01.1"}), gold_db, csv)
    df = gold.read_labels(gold_db)
    assert len(df) == 1 and df.iloc[0]["field_primary"] == "S01.1"
    assert df.iloc[0]["fields_secondary"] == ["S06.2"]
    exported = pd.read_csv(csv)
    assert exported.iloc[0]["project_id"] == "gh:a/b" and json.loads(exported.iloc[0]["fields_secondary"]) == ["S06.2"]


def test_import_csv_restores_labels(gold_db, tmp_path, monkeypatch):
    csv = tmp_path / "gold.csv"
    gold.save_label(GoldLabel(project_id="gh:c/d", annotator="zw", asset_type="app", sector_primary="S09",
                              field_primary="S09.1"), gold_db, csv)
    fresh = db.init_db(tmp_path / "fresh.db")
    monkeypatch.setattr(gold, "ensure_projects", lambda p, ids: None)
    with db.connect(fresh) as conn:   # the project row must exist (foreign key)
        conn.execute("INSERT INTO projects (id, name, collected_at) VALUES ('gh:c/d', 'd', 't')")
    assert gold.import_csv(fresh, csv) == 1
    assert gold.read_labels(fresh).iloc[0]["sector_primary"] == "S09"


def test_agreement_pending_and_kappa():
    one = pd.DataFrame([{"project_id": "gh:a/b", "annotator": "zw", "asset_type": "mcp",
                         "sector_primary": "S01", "field_primary": "S01.1"}])
    assert "Pending" in agreement.render(one)
    rows = []
    for i, (x, y) in enumerate([("S01", "S01"), ("S02", "S02"), ("S03", "S01"), ("S01", "S01")]):
        rows += [{"project_id": f"p{i}", "annotator": "a", "asset_type": "app", "sector_primary": x, "field_primary": x},
                 {"project_id": f"p{i}", "annotator": "b", "asset_type": "app", "sector_primary": y, "field_primary": y}]
    n, res = agreement.agreement(pd.DataFrame(rows), "a", "b")
    assert n == 4 and res["sector_primary"][1] == 0.75 and 0 < res["sector_primary"][0] < 1
