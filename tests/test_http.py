import httpx

from atlas import http


def make_client(tmp_path, handler, **kw):
    return http.CachedClient("t", cache_dir=tmp_path, transport=httpx.MockTransport(handler),
                             backoff_base=0, **kw)


def test_second_call_is_served_from_cache(tmp_path):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(200, json={"ok": True}, headers={"link": '<x>; rel="next"'})

    c = make_client(tmp_path, handler)
    r1 = c.get("https://api.example.com/x", params={"q": "a b"})
    c2 = make_client(tmp_path, handler)          # fresh client = a re-run of the script
    r2 = c2.get("https://api.example.com/x", params={"q": "a b"})
    assert len(calls) == 1
    assert r1.json() == r2.json() == {"ok": True}
    assert r2.from_cache and r2.headers["link"].startswith("<x>")


def test_404_cached_and_5xx_retried_not_cached(tmp_path):
    seq = iter([503, 200])
    calls = []

    def handler(req):
        calls.append(1)
        if "missing" in str(req.url):
            return httpx.Response(404, text="nope")
        return httpx.Response(next(seq), text="body")

    c = make_client(tmp_path, handler)
    assert c.get("https://a.test/missing").status == 404
    assert c.get("https://a.test/missing").from_cache
    assert c.get("https://a.test/flaky").status == 200
    assert len(calls) == 3   # 404 once, 503 then 200


def test_auth_header_never_cached(tmp_path, monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "secret-token-value")
    c = http.CachedClient("t", cache_dir=tmp_path, headers=http.github_headers(),
                          transport=httpx.MockTransport(lambda r: httpx.Response(200, text="ok")))
    c.get("https://api.github.com/x")
    import gzip
    for p in tmp_path.rglob("*.gz"):
        assert "secret-token-value" not in gzip.open(p, "rt").read()
