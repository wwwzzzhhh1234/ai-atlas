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
