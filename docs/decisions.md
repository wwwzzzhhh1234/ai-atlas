# Decisions log

Format: date · decision · reason. Newest at the bottom.

| Date | Decision | Reason |
|---|---|---|
| 2026-11-21 | Use a `src/` layout with `pyproject.toml`; install with `pip install -e .` | Makes `python -m atlas.db init` work from any folder on Windows and Linux |
| 2026-11-21 | Added `status` (`ok`/`failed`) and `error` columns to `labels` | Spec Section 8 says failed items are "marked `failed`"; Section 6 had no column for it. Added now because schema changes after M1 need approval |
| 2026-11-21 | Added `labeled_at` to `gold_labels` and `dim` to `embeddings` | Audit trail for annotation; lets us decode vector blobs safely |
| 2026-11-21 | SQLite stores JSON lists as TEXT, booleans as 0/1, dates as ISO-8601 TEXT; `PRAGMA user_version` = schema version | SQLite has no native list/bool/date types; version check prevents silent schema drift |
| 2026-11-21 | `gh:` ids lowercase; `hf:` and `mcp:` ids keep original case | Spec says lowercase for GitHub; HF repo ids are case-sensitive |
| 2026-11-21 | `inputs`/`outputs` tags only checked for shape (lowercase slug) until M3 | Controlled vocabulary is an M3 task |
| 2026-11-21 | `max_usd_per_run: 5.00` in `config/models.yaml` is a **placeholder** | Real budget cap is an open question (spec Section 12); kept low so nothing expensive can run by accident |
| 2026-11-21 | Gemini model IDs left `null`; Hydrogen price left `null` | Rule 2 (never invent data): must be read from Google AI Studio |
| 2026-11-21 | Default embedding model `BAAI/bge-small-en-v1.5` (fallback `all-MiniLM-L6-v2`) | Small, free, runs on a laptop CPU; revisit in M4 if quality is poor |
| 2026-11-21 | GitHub date slicing starts at 2018-01-01 (separate from the freshness filter) | Older but still active repos (e.g. pushed recently) must not be missed by the slicer |
| 2026-11-22 | GitHub metadata comes from the **REST Search API** only (no GraphQL, no per-repo `/repos` calls). Repos found by name (SKILL.md search, curated lists, MCP Registry) are looked up with batched `repo:a/b repo:c/d fork:true` search queries | GraphQL and per-repo REST calls are blocked in the cloud session; search results already contain every metadata field we need. Same code works on the laptop with a personal token |
| 2026-11-22 | READMEs fetched from `raw.githubusercontent.com/<repo>/HEAD/<README variant>` | Uses no API quota; works without a token |
| 2026-11-22 | Freshness pushed into the search query: run each query with `pushed:>=cutoff` **and** `created:>=2025-01-01 pushed:<cutoff` | Exactly the spec rule (created ≥ 2025-01-01 OR pushed within 12 months) while not paging through stale repos |
| 2026-11-22 | Adaptive slicing (split by stars, then by creation date) instead of fixed star ranges | Guarantees every slice is under the 1,000-result cap whatever the topic size |
| 2026-11-22 | `snapshot_date: 2026-11-22` in `sources.yaml`; the pushed cutoff is derived from it, not from today's date | Query strings — and therefore cache keys — stay identical on re-runs, so re-runs make no new calls |
| 2026-11-22 | HTTP cache: gzipped JSON per URL under `data/cache/http/<source>/`; caches 200 and 404 (HF also 401/403 for gated cards); retries 403/429/5xx with backoff; atomic writes | Resumable and idempotent (spec rule 5); a crash never leaves a corrupt cache file |
| 2026-11-22 | Star thresholds per provenance group: topics 100, non-niche keyword groups 100, niche groups 20, SKILL.md repos 20, MCP Registry repos 20, curated-list links 0 (but must look AI-related) | Starting guesses; spec says thresholds are flexible for niche sources. Revisit with the report |
| 2026-11-22 | Hugging Face: top 2,000 models and 2,000 Spaces by likes, `likes >= 50`; ids `hf:owner/name` (models) and `hf:spaces/owner/name` (Spaces); called via the Hub REST API rather than `huggingface_hub` | Models and Spaces can share a name; REST lets every page go through the same cache |
| 2026-11-22 | MCP Registry API `v0.1`, `version=latest`, only `status: active`. Servers without a GitHub repo become `mcp:<name>` but are excluded by the README rule | Spec rule "README ≥ 200 chars"; counted in the report so we can revisit |
| 2026-11-22 | Schema v2 (still in M1, so no approval needed): `projects` gains `likes`, `downloads`, `readme_chars`, `collect_groups`, `included`, `exclude_reason`; automatic v1→v2 migration | M2 stratified sampling needs provenance groups; filter reasons make the funnel auditable. **Schema is frozen after M1** |
| 2026-11-22 | `projects` keeps every collected record (with `included` + `exclude_reason`); `candidates.parquet` has only included rows | Full funnel stays auditable without re-collecting |
| 2026-11-22 | Repo is **private**, so `data/processed/candidates.parquet` (with internal README excerpts) is committed. If the repo is made public, drop `readme_excerpt` from committed files first | Spec rule 10 |
