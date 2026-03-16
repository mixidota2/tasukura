"""タスクと進捗ログのデータモデル."""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timezone

from ulid import ULID


class TaskStatus(str, enum.Enum):
    """タスクのステータス."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


@dataclass(frozen=True)
class Task:
    """タスク."""

    id: str
    title: str
    status: TaskStatus
    jira_key: str | None
    created_at: str
    updated_at: str

    @classmethod
    def new(cls, title: str, jira_key: str | None = None) -> Task:
        """新しいタスクを作成する."""
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(ULID()),
            title=title,
            status=TaskStatus.TODO,
            jira_key=jira_key,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class ProgressLog:
    """進捗ログ."""

    id: str
    task_id: str
    summary: str
    details: str | None
    remaining: str | None
    created_at: str

    @classmethod
    def new(
        cls,
        task_id: str,
        summary: str,
        details: str | None = None,
        remaining: str | None = None,
    ) -> ProgressLog:
        """新しい進捗ログを作成する."""
        return cls(
            id=str(ULID()),
            task_id=task_id,
            summary=summary,
            details=details,
            remaining=remaining,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
