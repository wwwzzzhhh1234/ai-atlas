# Progress log

**Current milestone: M1 — Collection** (M0 complete, see below)

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
