"""Data models for tasks and progress logs."""

import enum
from dataclasses import dataclass
from datetime import datetime, timezone

from ulid import ULID


class TaskStatus(str, enum.Enum):
    """Task status."""

    TODO = "todo"
    IN_PROGRESS = "in_progress"
    IN_REVIEW = "in_review"
    DONE = "done"


@dataclass(frozen=True)
class Task:
    """A task."""

    id: str
    title: str
    description: str
    status: TaskStatus
    source_id: str | None
    source: str | None
    parent_id: str | None
    next_action: str | None
    position: int
    created_at: str
    updated_at: str

    @classmethod
    def new(
        cls,
        title: str,
        description: str,
        source_id: str | None = None,
        source: str | None = None,
        parent_id: str | None = None,
        next_action: str | None = None,
        position: int = 0,
    ) -> "Task":
        """Create a new task."""
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(ULID()),
            title=title,
            description=description,
            status=TaskStatus.TODO,
            source_id=source_id,
            source=source,
            parent_id=parent_id,
            next_action=next_action,
            position=position,
            created_at=now,
            updated_at=now,
        )


@dataclass(frozen=True)
class ProgressLog:
    """A progress log entry."""

    id: str
    task_id: str
    summary: str
    details: str | None
    remaining: str | None
    next_action_set: str | None
    created_at: str

    @classmethod
    def new(
        cls,
        task_id: str,
        summary: str,
        details: str | None = None,
        remaining: str | None = None,
        next_action_set: str | None = None,
    ) -> "ProgressLog":
        """Create a new progress log entry."""
        return cls(
            id=str(ULID()),
            task_id=task_id,
            summary=summary,
            details=details,
            remaining=remaining,
            next_action_set=next_action_set,
            created_at=datetime.now(timezone.utc).isoformat(),
        )


class RecordKind(str, enum.Enum):
    """Kind of typed record."""

    DECISION = "decision"
    FINDING = "finding"
    BLOCKER = "blocker"
    QUESTION = "question"
    HYPOTHESIS = "hypothesis"


class RecordStatus(str, enum.Enum):
    """Status of a typed record."""

    ACTIVE = "active"
    SUPERSEDED = "superseded"
    OBSOLETE = "obsolete"
    RESOLVED = "resolved"  # blocker only


@dataclass(frozen=True)
class Record:
    """A typed knowledge record (decision / finding / blocker / question / hypothesis)."""

    id: str
    task_id: str
    kind: RecordKind
    status: RecordStatus
    summary: str
    details: str | None
    supersedes: str | None
    source_log_id: str
    resolved_at: str | None
    last_verified_at: str | None
    created_at: str
    updated_at: str

    @classmethod
    def new(
        cls,
        task_id: str,
        kind: RecordKind,
        source_log_id: str,
        summary: str,
        details: str | None = None,
        supersedes: str | None = None,
    ) -> "Record":
        """Create a new active record. source_log_id is required (promotion gate)."""
        now = datetime.now(timezone.utc).isoformat()
        return cls(
            id=str(ULID()),
            task_id=task_id,
            kind=kind,
            status=RecordStatus.ACTIVE,
            summary=summary,
            details=details,
            supersedes=supersedes,
            source_log_id=source_log_id,
            resolved_at=None,
            last_verified_at=None,
            created_at=now,
            updated_at=now,
        )
