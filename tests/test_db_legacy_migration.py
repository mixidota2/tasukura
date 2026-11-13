"""Synthetic legacy schemas, not snapshots of users' historical databases."""

import sqlite3
from pathlib import Path

import pytest

from tasukura.db import TaskDB
from tasukura.models import TaskStatus


@pytest.mark.parametrize(
    "shape", ["pre_description_jira", "partial_migration", "existing_external_source"]
)
def test_legacy_migration_preserves_data_and_is_repeatable(tmp_path: Path, shape: str):
    path = tmp_path / "tasks.db"
    with sqlite3.connect(path) as conn:
        conn.executescript("""
            CREATE TABLE tasks (
                id TEXT PRIMARY KEY, title TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'todo', jira_key TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE TABLE progress_logs (
                id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id),
                summary TEXT NOT NULL, details TEXT, remaining TEXT,
                created_at TEXT NOT NULL
            );
        """)
        conn.execute(
            "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?)",
            (
                "legacy-task",
                "既存の依頼",
                "in_progress",
                "OLD-42",
                "2025-01-01",
                "2025-01-02",
            ),
        )
        conn.execute(
            "INSERT INTO progress_logs VALUES (?, ?, ?, ?, ?, ?)",
            (
                "legacy-log",
                "legacy-task",
                "保存済みの進捗",
                "原文詳細",
                "未完の仕事",
                "2025-01-02",
            ),
        )
        if shape != "pre_description_jira":
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''"
            )
            conn.execute("UPDATE tasks SET description = '保持する説明'")
            conn.execute(
                "ALTER TABLE tasks ADD COLUMN parent_id TEXT REFERENCES tasks(id)"
            )
        if shape == "existing_external_source":
            conn.execute("ALTER TABLE tasks ADD COLUMN source_id TEXT")
            conn.execute("ALTER TABLE tasks ADD COLUMN source TEXT")
            conn.execute("UPDATE tasks SET source_id = 'gh-9', source = 'github'")
        original_logs = conn.execute(
            "SELECT id, task_id, summary, details, remaining, created_at FROM progress_logs"
        ).fetchall()
    conn.close()

    with TaskDB(path) as db:
        old = db.get_task("legacy-task")
        assert old is not None
        assert old.title == "既存の依頼"
        assert old.status == TaskStatus.IN_PROGRESS
        assert old.created_at == "2025-01-01"
        assert old.updated_at == "2025-01-02"
        expected_source = (
            ("gh-9", "github")
            if shape == "existing_external_source"
            else ("OLD-42", "jira")
        )
        assert (old.source_id, old.source) == expected_source
        assert old.description == (
            "" if shape == "pre_description_jira" else "保持する説明"
        )
        assert (
            db._conn.execute(
                "SELECT id, task_id, summary, details, remaining, created_at FROM progress_logs"
            ).fetchall()
            == original_logs
        )
        child = db.add_task("移行後の追加", "新しい説明", parent_id=old.id)
        migrated_tasks = db._conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()

    with TaskDB(path) as db:
        assert (
            db._conn.execute("SELECT * FROM tasks ORDER BY id").fetchall()
            == migrated_tasks
        )
        assert (
            db._conn.execute(
                "SELECT id, task_id, summary, details, remaining, created_at FROM progress_logs"
            ).fetchall()
            == original_logs
        )
        saved_child = db.get_task(child.id)
        assert saved_child is not None
        assert saved_child.parent_id == "legacy-task"
        assert saved_child.title == "移行後の追加"
        assert saved_child.description == "新しい説明"
        assert db._conn.execute("PRAGMA integrity_check").fetchall() == [("ok",)]
        assert db._conn.execute("PRAGMA foreign_key_check").fetchall() == []
