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
