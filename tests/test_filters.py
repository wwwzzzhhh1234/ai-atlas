from atlas.clean import filters
from atlas.collect.common import new_record


def rec(**kw):
    base = dict(name="x", stars=150, created_at="2025-03-01", pushed_at="2025-03-01",
                is_fork=False, is_archived=False)
    base.update(kw)
    group = base.pop("group", "topic:llm")
    return new_record("gh:o/x", source="github", group=group, **base)


def test_keeps_good_record():
    assert filters.metadata_exclusion(rec()) is None


def test_reasons():
    assert filters.metadata_exclusion(rec(stars=None)) == "metadata_not_found"
    assert filters.metadata_exclusion(rec(is_fork=True)) == "fork"
    assert filters.metadata_exclusion(rec(is_archived=True)) == "archived"
    assert filters.metadata_exclusion(rec(created_at="2020-01-01", pushed_at="2023-01-01")) == "stale"
    assert filters.metadata_exclusion(rec(stars=50)) == "low_stars"


def test_freshness_by_push_date():
    assert filters.is_fresh(rec(created_at="2019-01-01", pushed_at="2026-10-01"))


def test_niche_and_group_thresholds():
    assert filters.min_stars_for(rec(group="kw:smart_city_transport")) == 20
    assert filters.min_stars_for(rec(group="kw:healthcare")) == 20      # niche since 2026-11-22
    assert filters.min_stars_for(rec(group="kw:finance_legal")) == 100
    assert filters.metadata_exclusion(rec(stars=25, group="kw:startup")) is None


def test_ai_related_for_curated_links():
    assert not filters.is_ai_related(rec(group="curated:x/y", name="left-pad", description="Pads strings"))
    assert filters.is_ai_related(rec(group="curated:x/y", name="pdf-skill", description="An agent skill"))
    assert filters.metadata_exclusion(rec(group="curated:x/y", name="left-pad", description="pads")) == "not_ai_related"


def test_readme_exclusion():
    assert filters.readme_exclusion({"has_readme": False}) == "no_readme"
    assert filters.readme_exclusion({"has_readme": True, "readme_chars": 50}) == "short_readme"
    assert filters.readme_exclusion({"has_readme": True, "readme_chars": 500}) is None


def test_registry_only_repo_without_metadata():
    r = rec(stars=None, group="mcp_registry")
    assert filters.metadata_exclusion(r) == "not_found_by_search"
    r["groups"].add("skill_file")
    assert filters.metadata_exclusion(r) == "metadata_not_found"


def test_mcp_keyword_group_threshold():
    assert filters.min_stars_for(rec(group="kw:mcp_servers")) == 20


def test_hf_space_informative_threshold():
    space = new_record("hf:spaces/a/b", source="huggingface", group="hf_space", has_readme=True, readme_chars=10)
    space["informative_chars"] = 99
    assert filters.readme_exclusion(space) == "too_little_info"
    space["informative_chars"] = 150
    assert filters.readme_exclusion(space) is None


def test_v1_label_set_tiers():
    from atlas.select import in_v1_label_set
    assert in_v1_label_set(150, None, ["topic:llm"])
    assert not in_v1_label_set(60, None, ["kw:mcp_servers"])       # general MCP 20-99 -> later
    assert in_v1_label_set(25, None, ["kw:healthcare"])             # niche keeps >= 20
    assert not in_v1_label_set(15, None, ["kw:healthcare"])
    assert in_v1_label_set(None, 80, ["hf_space"]) and not in_v1_label_set(None, None, ["mcp_registry"])
    assert filters.min_stars_for(rec(group="curated:a/b")) == 20
