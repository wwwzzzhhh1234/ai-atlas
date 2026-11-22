# Progress log

**Current milestone: M1 — Collection: all 3 checks done, waiting for human review of 3 tuning decisions (see 2026-11-22). Next: M2 — Gold set**

---

## 2026-11-21 — M0 Setup ✅

Done
- Repo skeleton per spec Section 11; `PROJECT_SPEC.md`, `CLAUDE.md`, `README.md`, `requirements.txt`, `pyproject.toml`.
- `.env.example` (`GITHUB_TOKEN`, `GEMINI_API_KEY`); `.gitignore` covers `.env`, `data/raw`, `data/cache`, `data/*.db`.
- `config/taxonomy.yaml` (verbatim from spec Section 5), `config/sources.yaml`, `config/models.yaml`.
- `src/atlas/`: `paths.py`, `config.py`, `taxonomy.py` (loader + lookups), `schema.py` (pydantic v2 models
  with taxonomy-aware validation), `db.py` (SQLite schema v1 + CLI).
- Docs skeletons: `decisions.md`, `progress_log.md`, `annotation_guideline.md`.

"Done when" checks
- [x] `pytest` passes — 30 tests (taxonomy, schema, db).
- [x] `python -m atlas.db init` creates an empty database (5 tables, 0 rows; idempotent).
- [x] Taxonomy loader reports `Taxonomy v3: 10 sectors / 50 fields`.

Waiting on the human
- Push this repo to GitHub as `ai-atlas` (not yet created).
- Create `.env` with a GitHub token (needed for M1).
- Gemini model IDs + prices (needed by M3, not M1).
- Budget cap (placeholder $5/run for now).

Next (M1)
- GitHub collector (topics, keyword groups, star/date slicing, GraphQL metadata, README fetch, cache, backoff).
- MCP Registry collector, Hugging Face collector, cleaning + filters + de-dup, report script.

---

## 2026-11-22 — M1 Collection ✅ (pending human sign-off)

Done
- Repo pushed to GitHub (`wwwzzzhhh1234/ai-atlas`, private).
- Collectors: GitHub (20 topics, 7 keyword groups, SKILL.md code search, 3 curated lists, batched repo lookups,
  READMEs via raw.githubusercontent.com), MCP Registry (v0.1), Hugging Face (top 2,000 models + 2,000 Spaces by likes).
- Cleaning: README cleanup, inclusion filters (spec Section 7), de-dup/merge by canonical id.
- Cached HTTP client → resumable/idempotent; report script; spot-check sampler. 55 tests pass.
- Schema v2 (provenance groups, inclusion flag, exclusion reason). **Schema is now frozen** (changes need approval).

Real numbers (snapshot_date 2026-11-22; full report: `reports/collection_report.md`)
- Collected 89,314 unique projects → **26,349 included** (24,881 GitHub-sourced · 1,468 Hugging Face · 1,899 also in MCP Registry).
- First run: 23,997 HTTP calls, 0 errors, 68 min. Exclusions: not_found_by_search 31,601 (registry repos < 20 stars) ·
  no_readme 25,780 (mostly remote-only registry servers) · low_stars 3,056 · stale 1,610 · short_readme 900 · other 18.
- Largest groups (included): kw:mcp_servers 15,100 · topic:llm 4,936 · topic:ai-agents 3,743 · topic:mcp 3,368.
- Niche keyword groups (included): governance_safety 1,486 · startup 78 · finance_legal 59 · healthcare 13 ·
  smart_city_transport 12 · agriculture_climate 11.
- Stars (included GitHub): 20–49: 7,571 · 50–99: 3,550 · 100–199: 5,094 · 200–999: 5,613 · 1k+: 3,031.

"Done when" checks
- [x] `python -m atlas.collect.run` is resumable; full re-run made **0 network calls** (30,371 cache hits, 43 s).
- [x] `data/processed/candidates.parquet` exists (26,349 rows; README excerpts sharded in `data/processed/readmes/`).
- [x] 20 random rows checked (`docs/m1_spotcheck.md`): 0 junk, 0 wrong merges; 3 borderline. **Human to confirm.**

Decisions needed from the human (thresholds are "starting guesses" per spec Section 7)
1. **Pool is 2.6× the ~10k target**, driven by MCP repos at 20–99 stars (kw:mcp_servers). Options: raise MCP threshold
   to 50 (≈ −6k) or 100 (≈ −10k); or keep everything and label only a subset first.
2. **Niche sectors are thin** (healthcare 13, smart city 12, agriculture 11): keyword queries require all words
   (e.g. "clinical llm"). Proposal: broaden to more, shorter queries per sector before M2 so the gold set has examples.
3. **HF Spaces mostly excluded** (349 / 2,000): their README is often only config. Option: accept the Space's
   short description in place of a README for HF Spaces.

Known limitations
- `github/awesome-copilot` yields 1 link (its README links to its own files, not other repos).
- GitHub GraphQL / per-repo REST are blocked in the cloud session → Search API + raw.githubusercontent.com used instead.

Next (M2) after sign-off
- Stratified sample of ~250 (by provenance group + rough asset type), annotation guideline, labeling tool (Streamlit).
