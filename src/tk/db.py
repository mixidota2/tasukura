"""SQLiteによるタスクとログの永続化."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from tk.models import ProgressLog, Task, TaskStatus

DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tk" / "tasks.db"

_TASK_COLUMNS = "id, title, description, status, jira_key, parent_id, next_action, created_at, updated_at"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'todo',
    jira_key    TEXT,
    parent_id   TEXT REFERENCES tasks(id),
    next_action TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
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

_MIGRATIONS = [
    "ALTER TABLE tasks ADD COLUMN description TEXT NOT NULL DEFAULT ''",
    "ALTER TABLE tasks ADD COLUMN parent_id TEXT REFERENCES tasks(id)",
    "ALTER TABLE tasks ADD COLUMN next_action TEXT",
]


class TaskDB:
    """タスクDBの操作を提供する."""

    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._run_migrations()

    def _run_migrations(self) -> None:
        """マイグレーションを実行する。既存DBへのカラム追加等."""
        for migration in _MIGRATIONS:
            try:
                self._conn.execute(migration)
                self._conn.commit()
            except sqlite3.OperationalError:
                # カラムが既に存在する場合は無視
                pass

    def close(self) -> None:
        """DB接続を閉じる."""
        self._conn.close()

    @staticmethod
    def _row_to_task(r: tuple) -> Task:
        """DBの行をTaskに変換する。カラム順は _TASK_COLUMNS に従う."""
        return Task(
            id=r[0], title=r[1], description=r[2], status=TaskStatus(r[3]),
            jira_key=r[4], parent_id=r[5], next_action=r[6],
            created_at=r[7], updated_at=r[8],
        )

    def add_task(
        self,
        title: str,
        description: str,
        jira_key: str | None = None,
        parent_id: str | None = None,
        next_action: str | None = None,
    ) -> Task:
        """タスクを追加する."""
        task = Task.new(title=title, description=description, jira_key=jira_key, parent_id=parent_id, next_action=next_action)
        self._conn.execute(
            f"INSERT INTO tasks ({_TASK_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (task.id, task.title, task.description, task.status.value, task.jira_key, task.parent_id, task.next_action, task.created_at, task.updated_at),
        )
        self._conn.commit()
        return task

    def get_task(self, task_id: str) -> Task | None:
        """タスクをIDで取得する."""
        row = self._conn.execute(f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def list_tasks(
        self,
        statuses: list[TaskStatus] | None = None,
        jira_only: bool = False,
    ) -> list[Task]:
        """タスク一覧を取得する."""
        query = f"SELECT {_TASK_COLUMNS} FROM tasks WHERE 1=1"
        params: list[str] = []

        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            params.extend(s.value for s in statuses)

        if jira_only:
            query += " AND jira_key IS NOT NULL"

        query += " ORDER BY created_at DESC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        jira_key: str | None = None,
        next_action: str | None = None,
    ) -> Task:
        """タスクのフィールドを更新する。指定されたフィールドのみ更新."""
        task = self.get_task(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise ValueError(msg)
        updates: list[str] = []
        params: list[str] = []
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        if description is not None:
            updates.append("description = ?")
            params.append(description)
        if jira_key is not None:
            updates.append("jira_key = ?")
            params.append(jira_key)
        if next_action is not None:
            updates.append("next_action = ?")
            params.append(next_action)
        if not updates:
            return task
        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)
        self._conn.execute(f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params)
        self._conn.commit()
        updated = self.get_task(task_id)
        assert updated is not None
        return updated

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
        # _TASK_COLUMNS のカラムをt.プレフィックス付きで生成
        task_cols = ", ".join(f"t.{c.strip()}" for c in _TASK_COLUMNS.split(","))
        rows = self._conn.execute(
            f"""
            SELECT {task_cols},
                   l.id, l.task_id, l.summary, l.details, l.remaining, l.created_at
            FROM progress_logs l
            JOIN tasks t ON t.id = l.task_id
            WHERE l.created_at LIKE ?
            ORDER BY l.created_at ASC
            """,
            (f"{date}%",),
        ).fetchall()
        task_col_count = len(_TASK_COLUMNS.split(","))
        return [
            (
                self._row_to_task(r[:task_col_count]),
                ProgressLog(id=r[task_col_count], task_id=r[task_col_count + 1], summary=r[task_col_count + 2], details=r[task_col_count + 3], remaining=r[task_col_count + 4], created_at=r[task_col_count + 5]),
            )
            for r in rows
        ]
