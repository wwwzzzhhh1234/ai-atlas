"""SQLite storage (spec Section 6).

CLI (PowerShell or any shell):
    python -m atlas.db init            # create data/atlas.db (idempotent)
    python -m atlas.db info            # list tables and row counts
    python -m atlas.db init --path X   # use another file
"""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from atlas.paths import DB_PATH

SCHEMA_VERSION = 2

# JSON-list columns are stored as TEXT holding a JSON array.
# Booleans are stored as INTEGER 0/1. Dates/datetimes as ISO-8601 TEXT.
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS projects (
    id              TEXT PRIMARY KEY,
    name            TEXT NOT NULL,
    url             TEXT,
    description     TEXT,
    sources         TEXT NOT NULL DEFAULT '[]',
    stars           INTEGER,
    forks           INTEGER,
    likes           INTEGER,                -- Hugging Face
    downloads       INTEGER,                -- Hugging Face
    created_at      TEXT,
    pushed_at       TEXT,
    license_spdx    TEXT,
    language        TEXT,
    topics          TEXT NOT NULL DEFAULT '[]',
    is_fork         INTEGER,
    is_archived     INTEGER,
    has_readme      INTEGER,
    readme_excerpt  TEXT,
    readme_chars    INTEGER,
    collect_groups  TEXT NOT NULL DEFAULT '[]',   -- provenance: topic:llm, kw:healthcare, mcp_registry, ...
    included        INTEGER NOT NULL DEFAULT 0,   -- 1 = passes all inclusion filters
    exclude_reason  TEXT,
    collected_at    TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS labels (
    project_id          TEXT NOT NULL REFERENCES projects(id),
    model               TEXT NOT NULL,
    prompt_version      TEXT NOT NULL,
    status              TEXT NOT NULL DEFAULT 'ok' CHECK (status IN ('ok', 'failed')),
    error               TEXT,
    asset_type          TEXT CHECK (asset_type IN
                          ('skill','mcp','agent','workflow','app','governance','model','resource')),
    sector_primary      TEXT,
    field_primary       TEXT,
    fields_secondary    TEXT NOT NULL DEFAULT '[]',
    business_summary    TEXT,
    developer_summary   TEXT,
    use_cases           TEXT NOT NULL DEFAULT '[]',
    non_tech_usability  INTEGER CHECK (non_tech_usability BETWEEN 1 AND 5),
    deploy_difficulty   INTEGER CHECK (deploy_difficulty BETWEEN 1 AND 5),
    inputs              TEXT NOT NULL DEFAULT '[]',
    outputs             TEXT NOT NULL DEFAULT '[]',
    confidence          REAL CHECK (confidence BETWEEN 0 AND 1),
    cost_usd            REAL,
    labeled_at          TEXT NOT NULL,
    PRIMARY KEY (project_id, model, prompt_version)
);

CREATE TABLE IF NOT EXISTS gold_labels (
    project_id        TEXT NOT NULL REFERENCES projects(id),
    annotator         TEXT NOT NULL,
    asset_type        TEXT NOT NULL,
    sector_primary    TEXT NOT NULL,
    field_primary     TEXT NOT NULL,
    fields_secondary  TEXT NOT NULL DEFAULT '[]',
    notes             TEXT,
    labeled_at        TEXT,
    PRIMARY KEY (project_id, annotator)
);

CREATE TABLE IF NOT EXISTS embeddings (
    project_id  TEXT NOT NULL REFERENCES projects(id),
    model       TEXT NOT NULL,
    dim         INTEGER NOT NULL,
    vector      BLOB NOT NULL,          -- float32 little-endian bytes
    PRIMARY KEY (project_id, model)
);

CREATE TABLE IF NOT EXISTS related (
    project_id  TEXT NOT NULL REFERENCES projects(id),
    related_id  TEXT NOT NULL REFERENCES projects(id),
    kind        TEXT NOT NULL CHECK (kind IN ('alternative', 'complement')),
    score       REAL NOT NULL,
    PRIMARY KEY (project_id, related_id, kind),
    CHECK (project_id <> related_id)
);

CREATE INDEX IF NOT EXISTS idx_projects_included ON projects(included);
CREATE INDEX IF NOT EXISTS idx_labels_sector ON labels(sector_primary);
CREATE INDEX IF NOT EXISTS idx_labels_field  ON labels(field_primary);
CREATE INDEX IF NOT EXISTS idx_related_rel   ON related(related_id);
"""

TABLES = ("projects", "labels", "gold_labels", "embeddings", "related")

# Forward migrations: MIGRATIONS[n] upgrades a database from version n to n + 1.
MIGRATIONS = {
    1: [
        "ALTER TABLE projects ADD COLUMN likes INTEGER",
        "ALTER TABLE projects ADD COLUMN downloads INTEGER",
        "ALTER TABLE projects ADD COLUMN readme_chars INTEGER",
        "ALTER TABLE projects ADD COLUMN collect_groups TEXT NOT NULL DEFAULT '[]'",
        "ALTER TABLE projects ADD COLUMN included INTEGER NOT NULL DEFAULT 0",
        "ALTER TABLE projects ADD COLUMN exclude_reason TEXT",
    ],
}


def connect(path: Path | str = DB_PATH) -> sqlite3.Connection:
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(path: Path | str = DB_PATH) -> Path:
    """Create the database and all tables. Safe to run repeatedly."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        current = conn.execute("PRAGMA user_version").fetchone()[0]
        if current > SCHEMA_VERSION:
            raise RuntimeError(f"{path} has schema v{current}; code expects v{SCHEMA_VERSION}")
        for v in range(current or SCHEMA_VERSION, SCHEMA_VERSION):
            for stmt in MIGRATIONS[v]:
                conn.execute(stmt)
        conn.executescript(SCHEMA_SQL)
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    return path


def table_counts(path: Path | str = DB_PATH) -> dict[str, int]:
    with connect(path) as conn:
        return {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABLES}


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(prog="python -m atlas.db")
    parser.add_argument("command", choices=["init", "info"])
    parser.add_argument("--path", type=Path, default=DB_PATH)
    args = parser.parse_args(argv)
    if args.command == "init":
        p = init_db(args.path)
        print(f"Database ready at {p} (schema v{SCHEMA_VERSION})")
    for table, n in table_counts(args.path).items():
        print(f"  {table:<12} {n} rows")



PROJECT_COLUMNS = (
    "id", "name", "url", "description", "sources", "stars", "forks", "likes", "downloads",
    "created_at", "pushed_at", "license_spdx", "language", "topics", "is_fork", "is_archived",
    "has_readme", "readme_excerpt", "readme_chars", "collect_groups", "included", "exclude_reason",
    "collected_at",
)


def upsert_projects(conn: sqlite3.Connection, rows: list[dict]) -> int:
    """Insert or update project rows (dicts keyed by PROJECT_COLUMNS, JSON fields already encoded).

    Uses ON CONFLICT ... DO UPDATE (not REPLACE) so rows referenced by labels are never deleted.
    """
    cols = ", ".join(PROJECT_COLUMNS)
    marks = ", ".join(f":{c}" for c in PROJECT_COLUMNS)
    updates = ", ".join(f"{c} = excluded.{c}" for c in PROJECT_COLUMNS if c != "id")
    sql = f"INSERT INTO projects ({cols}) VALUES ({marks}) ON CONFLICT(id) DO UPDATE SET {updates}"
    conn.executemany(sql, rows)
    return len(rows)


if __name__ == "__main__":
    main()
