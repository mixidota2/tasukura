"""SQLiteによるタスクとログの永続化."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from tk.models import ProgressLog, Task, TaskStatus

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tk" / "tasks.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id         TEXT PRIMARY KEY,
    title      TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'todo',
    jira_key   TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS progress_logs (
    id         TEXT PRIMARY KEY,
    task_id    TEXT NOT NULL REFERENCES tasks(id),
    summary    TEXT NOT NULL,
    details    TEXT,
    remaining  TEXT,
    created_at TEXT NOT NULL
);
"""


class TaskDB:
    """タスクDBの操作を提供する."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)

    def close(self) -> None:
        """DB接続を閉じる."""
        self._conn.close()

    def add_task(self, title: str, jira_key: str | None = None) -> Task:
        """タスクを追加する."""
        task = Task.new(title=title, jira_key=jira_key)
        self._conn.execute(
            "INSERT INTO tasks (id, title, status, jira_key, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
            (task.id, task.title, task.status.value, task.jira_key, task.created_at, task.updated_at),
        )
        self._conn.commit()
        return task

    def get_task(self, task_id: str) -> Task | None:
        """タスクをIDで取得する."""
        row = self._conn.execute("SELECT id, title, status, jira_key, created_at, updated_at FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return Task(id=row[0], title=row[1], status=TaskStatus(row[2]), jira_key=row[3], created_at=row[4], updated_at=row[5])

    def list_tasks(
        self,
        statuses: list[TaskStatus] | None = None,
        jira_only: bool = False,
    ) -> list[Task]:
        """タスク一覧を取得する."""
        query = "SELECT id, title, status, jira_key, created_at, updated_at FROM tasks WHERE 1=1"
        params: list[str] = []

        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            params.extend(s.value for s in statuses)

        if jira_only:
            query += " AND jira_key IS NOT NULL"

        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [Task(id=r[0], title=r[1], status=TaskStatus(r[2]), jira_key=r[3], created_at=r[4], updated_at=r[5]) for r in rows]

    def update_status(self, task_id: str, status: TaskStatus) -> Task:
        """タスクのステータスを更新する."""
        task = self.get_task(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise ValueError(msg)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute("UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?", (status.value, now, task_id))
        self._conn.commit()
        updated = self.get_task(task_id)
        assert updated is not None
        return updated

    def add_log(
        self,
        task_id: str,
        summary: str,
        details: str | None = None,
        remaining: str | None = None,
    ) -> ProgressLog:
        """進捗ログを追加する."""
        log = ProgressLog.new(task_id=task_id, summary=summary, details=details, remaining=remaining)
        self._conn.execute(
            "INSERT INTO progress_logs (id, task_id, summary, details, remaining, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (log.id, log.task_id, log.summary, log.details, log.remaining, log.created_at),
        )
        self._conn.commit()
        return log

    def get_logs(self, task_id: str) -> list[ProgressLog]:
        """タスクの進捗ログを取得する."""
        rows = self._conn.execute(
            "SELECT id, task_id, summary, details, remaining, created_at FROM progress_logs WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()
        return [ProgressLog(id=r[0], task_id=r[1], summary=r[2], details=r[3], remaining=r[4], created_at=r[5]) for r in rows]

    def get_daily_logs(self, date: str | None = None) -> list[tuple[Task, ProgressLog]]:
        """指定日の進捗ログをタスクと一緒に取得する.

        Args:
            date: YYYY-MM-DD形式。Noneの場合は今日。
        """
        if date is None:
            date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        rows = self._conn.execute(
            """
            SELECT t.id, t.title, t.status, t.jira_key, t.created_at, t.updated_at,
                   l.id, l.task_id, l.summary, l.details, l.remaining, l.created_at
            FROM progress_logs l
            JOIN tasks t ON t.id = l.task_id
            WHERE l.created_at LIKE ?
            ORDER BY l.created_at ASC
            """,
            (f"{date}%",),
        ).fetchall()
        return [
            (
                Task(id=r[0], title=r[1], status=TaskStatus(r[2]), jira_key=r[3], created_at=r[4], updated_at=r[5]),
                ProgressLog(id=r[6], task_id=r[7], summary=r[8], details=r[9], remaining=r[10], created_at=r[11]),
            )
            for r in rows
        ]
