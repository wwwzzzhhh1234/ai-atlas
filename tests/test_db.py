import sqlite3

import pytest

from atlas import db


def test_init_creates_empty_tables(tmp_path):
    path = db.init_db(tmp_path / "atlas.db")
    assert path.exists()
    assert db.table_counts(path) == {t: 0 for t in db.TABLES}


def test_init_is_idempotent(tmp_path):
    path = tmp_path / "atlas.db"
    db.init_db(path)
    db.init_db(path)
    with db.connect(path) as conn:
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_constraints(tmp_path):
    path = db.init_db(tmp_path / "atlas.db")
    with db.connect(path) as conn:
        conn.execute("INSERT INTO projects (id, name, collected_at) VALUES ('gh:a/b', 'b', '2026-11-21')")
        conn.execute("INSERT INTO projects (id, name, collected_at) VALUES ('gh:c/d', 'd', '2026-11-21')")
        with pytest.raises(sqlite3.IntegrityError):   # self-relation
            conn.execute("INSERT INTO related VALUES ('gh:a/b', 'gh:a/b', 'alternative', 0.9)")
        with pytest.raises(sqlite3.IntegrityError):   # bad kind
            conn.execute("INSERT INTO related VALUES ('gh:a/b', 'gh:c/d', 'similar', 0.9)")
        with pytest.raises(sqlite3.IntegrityError):   # unknown project (foreign key)
            conn.execute("INSERT INTO related VALUES ('gh:a/b', 'gh:x/y', 'complement', 0.5)")
        with pytest.raises(sqlite3.IntegrityError):   # score out of range
            conn.execute("INSERT INTO labels (project_id, model, prompt_version, non_tech_usability, labeled_at)"
                         " VALUES ('gh:a/b', 'm', 'v1', 9, '2026-11-21')")


def test_cli_init(tmp_path, capsys):
    db.main(["init", "--path", str(tmp_path / "cli.db")])
    out = capsys.readouterr().out
    assert "Database ready" in out and "projects" in out


def test_migrates_v1_database(tmp_path):
    path = tmp_path / "old.db"
    v1 = db.SCHEMA_SQL.split("CREATE TABLE IF NOT EXISTS labels")[0]
    for col in ("likes", "downloads", "readme_chars", "collect_groups", "included", "exclude_reason"):
        v1 = "\n".join(l for l in v1.split("\n") if not l.strip().startswith(col))
    with db.connect(path) as conn:
        conn.executescript(v1)
        conn.execute("PRAGMA user_version = 1")
    db.init_db(path)
    with db.connect(path) as conn:
        cols = {r[1] for r in conn.execute("PRAGMA table_info(projects)")}
        assert {"likes", "collect_groups", "included", "exclude_reason"} <= cols
        assert conn.execute("PRAGMA user_version").fetchone()[0] == db.SCHEMA_VERSION


def test_upsert_keeps_labeled_rows(tmp_path):
    import json
    path = db.init_db(tmp_path / "a.db")
    row = {c: None for c in db.PROJECT_COLUMNS}
    row.update(id="gh:a/b", name="b", sources=json.dumps(["github"]), topics="[]", collect_groups="[]",
               included=1, collected_at="2026-11-22")
    with db.connect(path) as conn:
        db.upsert_projects(conn, [row])
        conn.execute("INSERT INTO labels (project_id, model, prompt_version, labeled_at) VALUES ('gh:a/b','m','v','t')")
        db.upsert_projects(conn, [{**row, "name": "b2"}])
        assert conn.execute("SELECT name FROM projects").fetchone()[0] == "b2"
