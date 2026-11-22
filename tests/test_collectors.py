from datetime import date

from atlas.collect import github, huggingface, mcp_registry
from atlas.http import Response


def test_parse_repo_links():
    md = """- [A](https://github.com/acme/tool-one) and https://github.com/Foo/bar.git.
    - https://github.com/topics/llm  https://github.com/sponsors/x  [x](https://github.com/acme/tool-one/tree/main)"""
    assert github.parse_repo_links(md) == {"acme/tool-one", "Foo/bar"}


def test_batches_respect_length():
    names = [f"owner{i}/repository-name-{i}" for i in range(40)]
    batches = list(github._batches(names, max_len=240))
    assert sum(len(b) for b in batches) == 40
    for b in batches:
        assert len(" ".join(f"repo:{n}" for n in b)) + len(" fork:true") <= 240


def test_split_order():
    assert github._split(100, None, None, None) == [(100, 199, None, None), (200, None, None, None)]
    assert github._split(100, 199, None, None) == [(100, 149, None, None), (150, 199, None, None)]
    parts = github._split(150, 150, None, None)
    (_, _, a0, a1), (_, _, b0, b1) = parts
    assert a1 + __import__("datetime").timedelta(days=1) == b0 and a0 < a1
    assert github._split(150, 150, date(2025, 1, 1), date(2025, 1, 1)) is None


class FakeSearch:
    """Pretends 2,500 repos have stars 100..2599 (one per star value)."""
    def __init__(self):
        self.queries = []

    def get(self, url, params=None):
        import json, re
        q = params["q"]
        self.queries.append(q)
        m = re.search(r"stars:(?:>=(\d+)|(\d+)\.\.(\d+))", q)
        lo = int(m.group(1) or m.group(2))
        hi = int(m.group(3)) if m.group(3) else 2599
        stars = list(range(lo, min(hi, 2599) + 1))
        page = params["page"]
        items = [{"full_name": f"o/r{s}", "name": f"r{s}", "html_url": "u", "stargazers_count": s}
                 for s in stars[(page - 1) * 100: page * 100]]
        return Response(200, json.dumps({"total_count": len(stars), "items": items}), {}, url)


def test_search_repositories_slices_under_cap():
    fake = FakeSearch()
    items = list(github.search_repositories(fake, "topic:llm", 100))
    assert sorted(i["stargazers_count"] for i in items) == list(range(100, 2600))


def test_mcp_server_record():
    with_repo = {"server": {"name": "io.github.acme/crm", "repository": {"url": "https://github.com/Acme/crm-mcp.git"}},
                 "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active"}}}
    r = mcp_registry.server_record(with_repo)
    assert r["id"] == "gh:acme/crm-mcp" and r["full_name"] == "Acme/crm-mcp"
    remote = {"server": {"name": "ac.x/mcp", "title": "X", "description": "d"},
              "_meta": {"io.modelcontextprotocol.registry/official": {"status": "active",
                                                                      "publishedAt": "2026-01-02T00:00:00Z"}}}
    r = mcp_registry.server_record(remote)
    assert r["id"] == "mcp:ac.x/mcp" and r["has_readme"] is False and r["created_at"] == "2026-01-02"
    deleted = {"server": {"name": "z"}, "_meta": {"io.modelcontextprotocol.registry/official": {"status": "deleted"}}}
    assert mcp_registry.server_record(deleted) is None


def test_hf_item_record():
    item = {"id": "acme/space", "likes": 60, "createdAt": "2025-05-01T00:00:00Z",
            "tags": ["gradio", "region:us"], "cardData": {"title": "Acme", "license": "mit",
                                                          "short_description": "Does things"}}
    r = huggingface.item_record(item, "spaces")
    assert r["id"] == "hf:spaces/acme/space" and r["license_spdx"] == "MIT"
    assert r["topics"] == ["gradio"] and r["url"] == "https://huggingface.co/spaces/acme/space"
    m = huggingface.item_record({"id": "acme/model", "pipeline_tag": "text-generation"}, "models")
    assert m["id"] == "hf:acme/model" and m["topics"] == ["text-generation"]


def test_group_queries_expand_terms_modifiers_topics():
    grp = {"queries": ["clinical llm"], "terms": ["medical", "drug discovery"], "modifiers": ["ai", "llm"],
           "topics": ["medical-ai"]}
    assert github.group_queries(grp) == ["clinical llm", "medical ai", "medical llm", "drug discovery ai",
                                        "drug discovery llm", "topic:medical-ai"]


def test_hf_space_header_and_informative_text():
    item = {"id": "acme/tryon", "likes": 900, "sdk": "gradio", "tags": ["gradio", "region:us"],
            "cardData": {"title": "Virtual Try-On", "short_description": "Try clothes on a photo",
                         "models": ["acme/tryon-model"], "datasets": "acme/clothes"}}
    r = huggingface.item_record(item, "spaces")
    assert r["hf_informative"] == "Virtual Try-On Try clothes on a photo"
    assert "SDK: gradio" in r["hf_header"] and "Models used: acme/tryon-model" in r["hf_header"]
    assert "Datasets used: acme/clothes" in r["hf_header"]
    assert huggingface.item_record({"id": "a/m"}, "models")["hf_header"] is None
