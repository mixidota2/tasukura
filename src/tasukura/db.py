"""SQLite persistence for tasks and progress logs."""

import os
import sqlite3
import stat
from datetime import datetime, timezone
from pathlib import Path

from tasukura.models import ProgressLog, Task, TaskStatus

_TASK_COLUMNS = "id, title, description, status, source_id, source, parent_id, next_action, position, created_at, updated_at"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS tasks (
    id          TEXT PRIMARY KEY,
    title       TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    status      TEXT NOT NULL DEFAULT 'todo',
    source_id   TEXT,
    source      TEXT,
    parent_id   TEXT REFERENCES tasks(id),
    next_action TEXT,
    position    INTEGER NOT NULL DEFAULT 0,
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
    "ALTER TABLE tasks ADD COLUMN position INTEGER NOT NULL DEFAULT 0",
    "ALTER TABLE tasks ADD COLUMN source_id TEXT",
    "ALTER TABLE tasks ADD COLUMN source TEXT",
]


class TaskDB:
    """Task database operations."""

    def __init__(self, db_path: str | Path) -> None:
        path = Path(db_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # Restrict directory to owner-only access
        try:
            os.chmod(path.parent, stat.S_IRWXU)
        except OSError:
            pass
        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.executescript(_SCHEMA)
        self._run_migrations()
        # Restrict DB file to owner read/write only
        try:
            os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        except OSError:
            pass

    def __enter__(self) -> "TaskDB":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def _run_migrations(self) -> None:
        """Run migrations for existing databases."""
        for migration in _MIGRATIONS:
            try:
                self._conn.execute(migration)
                self._conn.commit()
            except sqlite3.OperationalError:
                pass
        # Migrate jira_key → source_id/source for existing databases
        try:
            self._conn.execute(
                "UPDATE tasks SET source_id = jira_key, source = 'jira'"
                " WHERE jira_key IS NOT NULL AND source_id IS NULL"
            )
            self._conn.commit()
        except sqlite3.OperationalError:
            pass

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    @staticmethod
    def _row_to_task(r: tuple) -> Task:
        """Convert a database row to a Task. Column order follows _TASK_COLUMNS."""
        return Task(
            id=r[0],
            title=r[1],
            description=r[2],
            status=TaskStatus(r[3]),
            source_id=r[4],
            source=r[5],
            parent_id=r[6],
            next_action=r[7],
            position=r[8],
            created_at=r[9],
            updated_at=r[10],
        )

    def _next_position(self) -> int:
        """Return the next position value for appending."""
        row = self._conn.execute(
            "SELECT COALESCE(MAX(position), -1) + 1 FROM tasks"
        ).fetchone()
        return row[0]

    def _min_position(self) -> int:
        """Return the minimum position value for prepending."""
        row = self._conn.execute(
            "SELECT COALESCE(MIN(position), 1) - 1 FROM tasks"
        ).fetchone()
        return row[0]

    def get_top_position(self) -> int:
        """Return a position value for prepending."""
        return self._min_position()

    def get_position_after(self, task_id: str) -> int:
        """Return a position for inserting after the specified task.

        Shifts subsequent task positions by +1 to make room.
        """
        task = self.get_task(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise ValueError(msg)
        self._conn.execute(
            "UPDATE tasks SET position = position + 1 WHERE position > ?",
            (task.position,),
        )
        self._conn.commit()
        return task.position + 1

    def add_task(
        self,
        title: str,
        description: str,
        source_id: str | None = None,
        source: str | None = None,
        parent_id: str | None = None,
        next_action: str | None = None,
        position: int | None = None,
    ) -> Task:
        """Add a task.

        Args:
            position: Appended to the end if not specified.
        """
        if position is None:
            position = self._next_position()
        task = Task.new(
            title=title,
            description=description,
            source_id=source_id,
            source=source,
            parent_id=parent_id,
            next_action=next_action,
            position=position,
        )
        self._conn.execute(
            f"INSERT INTO tasks ({_TASK_COLUMNS}) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                task.id,
                task.title,
                task.description,
                task.status.value,
                task.source_id,
                task.source,
                task.parent_id,
                task.next_action,
                task.position,
                task.created_at,
                task.updated_at,
            ),
        )
        self._conn.commit()
        return task

    def get_task(self, task_id: str) -> Task | None:
        """Get a task by ID."""
        row = self._conn.execute(
            f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
        if row is None:
            return None
        return self._row_to_task(row)

    def resolve_id(self, partial_id: str) -> str:
        """Resolve a partial task ID prefix to the full ID.

        Args:
            partial_id: A prefix of the task ID to search for.

        Returns:
            The full task ID if exactly one match is found.

        Raises:
            ValueError: If zero or multiple tasks match the prefix.
        """
        query = f"SELECT {_TASK_COLUMNS} FROM tasks WHERE id LIKE ? || '%'"
        rows = self._conn.execute(query, (partial_id,)).fetchall()
        if len(rows) == 0:
            msg = f"Task not found: {partial_id}"
            raise ValueError(msg)
        if len(rows) > 1:
            msg = f"Ambiguous ID: {partial_id} (matches {len(rows)} tasks)"
            raise ValueError(msg)
        return self._row_to_task(rows[0]).id

    def list_tasks(
        self,
        statuses: list[TaskStatus] | None = None,
        source: str | None = None,
        done_since: str | None = None,
        parent_id: str | None = None,
    ) -> list[Task]:
        """List tasks.

        Args:
            statuses: Filter by statuses.
            source: Filter by source type (e.g. "jira").
            done_since: Limit done tasks to those updated since this ISO8601 datetime.
                        None returns all done tasks.
            parent_id: Filter by parent task ID.
        """
        query = f"SELECT {_TASK_COLUMNS} FROM tasks WHERE 1=1"
        params: list[str] = []

        if statuses:
            placeholders = ",".join("?" for _ in statuses)
            query += f" AND status IN ({placeholders})"
            params.extend(s.value for s in statuses)

        if done_since:
            query += " AND (status != 'done' OR updated_at >= ?)"
            params.append(done_since)

        if source:
            query += " AND source = ?"
            params.append(source)

        if parent_id is not None:
            query += " AND parent_id = ?"
            params.append(parent_id)

        query += " ORDER BY position ASC"
        rows = self._conn.execute(query, params).fetchall()
        return [self._row_to_task(r) for r in rows]

    def update_task(
        self,
        task_id: str,
        title: str | None = None,
        description: str | None = None,
        source_id: str | None = None,
        source: str | None = None,
        next_action: str | None = None,
    ) -> Task:
        """Update task fields. Only specified fields are updated."""
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
        if source_id is not None:
            updates.append("source_id = ?")
            params.append(source_id)
        if source is not None:
            updates.append("source = ?")
            params.append(source)
        if next_action is not None:
            updates.append("next_action = ?")
            params.append(next_action)
        if not updates:
            return task
        now = datetime.now(timezone.utc).isoformat()
        updates.append("updated_at = ?")
        params.append(now)
        params.append(task_id)
        self._conn.execute(
            f"UPDATE tasks SET {', '.join(updates)} WHERE id = ?", params
        )
        self._conn.commit()
        updated = self.get_task(task_id)
        if updated is None:
            msg = f"Task {task_id} unexpectedly missing after update"
            raise RuntimeError(msg)
        return updated

    def rank_task(self, task_id: str, after_id: str | None = None) -> Task:
        """Change a task's display order.

        Args:
            task_id: The task to move.
            after_id: Place after this task. None moves to top.
        """
        task = self.get_task(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise ValueError(msg)

        if after_id is None:
            new_position = self._min_position()
        else:
            after_task = self.get_task(after_id)
            if after_task is None:
                msg = f"Task {after_id} not found"
                raise ValueError(msg)
            self._conn.execute(
                "UPDATE tasks SET position = position + 1 WHERE position > ?",
                (after_task.position,),
            )
            new_position = after_task.position + 1

        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE tasks SET position = ?, updated_at = ? WHERE id = ?",
            (new_position, now, task_id),
        )
        self._conn.commit()
        updated = self.get_task(task_id)
        if updated is None:
            msg = f"Task {task_id} unexpectedly missing after update"
            raise RuntimeError(msg)
        return updated

    def update_status(self, task_id: str, status: TaskStatus) -> Task:
        """Update a task's status."""
        task = self.get_task(task_id)
        if task is None:
            msg = f"Task {task_id} not found"
            raise ValueError(msg)
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE tasks SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, now, task_id),
        )
        self._conn.commit()
        updated = self.get_task(task_id)
        if updated is None:
            msg = f"Task {task_id} unexpectedly missing after update"
            raise RuntimeError(msg)
        return updated

    def add_log(
        self,
        task_id: str,
        summary: str,
        details: str | None = None,
        remaining: str | None = None,
    ) -> ProgressLog:
        """Add a progress log entry."""
        log = ProgressLog.new(
            task_id=task_id, summary=summary, details=details, remaining=remaining
        )
        self._conn.execute(
            "INSERT INTO progress_logs (id, task_id, summary, details, remaining, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (
                log.id,
                log.task_id,
                log.summary,
                log.details,
                log.remaining,
                log.created_at,
            ),
        )
        self._conn.commit()
        return log

    def get_logs(self, task_id: str) -> list[ProgressLog]:
        """Get progress logs for a task."""
        rows = self._conn.execute(
            "SELECT id, task_id, summary, details, remaining, created_at FROM progress_logs WHERE task_id = ? ORDER BY created_at ASC",
            (task_id,),
        ).fetchall()
        return [
            ProgressLog(
                id=r[0],
                task_id=r[1],
                summary=r[2],
                details=r[3],
                remaining=r[4],
                created_at=r[5],
            )
            for r in rows
        ]
