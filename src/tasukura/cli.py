"""tk - local task management CLI for AI agents."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer

from tasukura.config import TkConfig
from tasukura.db import TaskDB
from tasukura.models import Task, TaskStatus

app = typer.Typer(help="tk - local task management CLI for AI agents")

_config: TkConfig | None = None


def _get_config() -> TkConfig:
    """Get configuration (singleton)."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = TkConfig.load()
    return _config


def _get_db() -> TaskDB:
    """Get a database connection."""
    return TaskDB(_get_config().db_path)


def _done_since_cutoff() -> str:
    """Return the ISO8601 cutoff for displaying done tasks."""
    config = _get_config()
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.done_retention_days)
    return cutoff.isoformat()


def _short_id(task_id: str) -> str:
    """Return the first 12 characters of a task ID for display.

    The first 10 characters of a ULID encode the timestamp (ms precision),
    so 12 characters include 2 random characters for disambiguation.
    """
    return task_id[:12]


def _parse_status(value: str) -> TaskStatus:
    """Parse a status string, exiting with a clean error on invalid input."""
    try:
        return TaskStatus(value)
    except ValueError:
        valid = ", ".join(s.value for s in TaskStatus)
        typer.echo(f"Invalid status: {value!r} (valid: {valid})")
        raise typer.Exit(1)  # noqa: B904


@app.command()
def add(
    title: str,
    description: Annotated[
        str, typer.Option(help="Goal, acceptance criteria, and background")
    ],
    source_id: Annotated[
        Optional[str], typer.Option(help="External source ID (e.g. PROJ-123, #456)")
    ] = None,
    source: Annotated[
        Optional[str], typer.Option(help="Source type (e.g. jira, github)")
    ] = None,
    parent: Annotated[Optional[str], typer.Option(help="Parent task ID")] = None,
    next_action: Annotated[
        Optional[str], typer.Option(help="Next action to take")
    ] = None,
    top: Annotated[bool, typer.Option("--top", help="Add to the top")] = False,
    after: Annotated[
        Optional[str], typer.Option(help="Add after the specified task")
    ] = None,
) -> None:
    """Add a new task."""
    with _get_db() as db:
        parent_id = _resolve_id(db, parent) if parent else None
        position: int | None = None
        if top:
            position = db.get_top_position()
        elif after:
            after_id = _resolve_id(db, after)
            position = db.get_position_after(after_id)
        task = db.add_task(
            title,
            description=description,
            source_id=source_id,
            source=source,
            parent_id=parent_id,
            next_action=next_action,
            position=position,
        )
    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    typer.echo(f"  description: {task.description}")
    typer.echo(f"  status: {task.status.value}")
    if task.source_id:
        typer.echo(f"  source_id: {task.source_id}")
    if task.source:
        typer.echo(f"  source: {task.source}")
    if task.parent_id:
        typer.echo(f"  parent: {_short_id(task.parent_id)}")
    if task.next_action:
        typer.echo(f"  next: {task.next_action}")


@app.command("list")
def list_tasks(
    status: Annotated[
        Optional[str],
        typer.Option(help="Comma-separated statuses (e.g. todo,in_progress)"),
    ] = None,
    source: Annotated[
        Optional[str], typer.Option(help="Filter by source type (e.g. jira, github)")
    ] = None,
    flat: Annotated[bool, typer.Option("--flat", help="Flat list (no tree)")] = False,
    all_tasks: Annotated[
        bool, typer.Option("--all", help="Include all done tasks")
    ] = False,
) -> None:
    """List tasks. Defaults to tree view."""
    statuses = [_parse_status(s.strip()) for s in status.split(",")] if status else None
    with _get_db() as db:
        done_since = None if all_tasks else _done_since_cutoff()
        tasks = db.list_tasks(statuses=statuses, source=source, done_since=done_since)
    if not tasks:
        typer.echo("No tasks")
        return
    if flat:
        for t in tasks:
            _print_task_line(t)
    else:
        _print_task_tree(tasks)


def _print_task_line(t: Task, indent: str = "") -> None:
    """Print a single task line."""
    src = f" [{t.source_id}]" if t.source_id else ""
    next_act = f" -> {t.next_action}" if t.next_action else ""
    typer.echo(
        f"{indent}{_short_id(t.id)}  {t.status.value:<12} {t.title}{src}{next_act}"
    )


def _print_task_tree(tasks: list[Task]) -> None:
    """Print tasks in tree format. Root tasks (no parent) are displayed first."""
    children: dict[str | None, list[Task]] = {}
    for t in tasks:
        children.setdefault(t.parent_id, []).append(t)

    def _print_children(parent_id: str | None, indent: str) -> None:
        for child in children.get(parent_id, []):
            _print_task_line(child, indent)
            _print_children(child.id, indent + "  ")

    for t in children.get(None, []):
        _print_task_line(t)
        _print_children(t.id, "  ")

    displayed_ids = {t.id for t in tasks}
    for t in tasks:
        if t.parent_id is not None and t.parent_id not in displayed_ids:
            _print_task_line(t)


@app.command()
def update(
    task_id: str,
    title: Annotated[Optional[str], typer.Option(help="Task title")] = None,
    description: Annotated[
        Optional[str], typer.Option(help="Goal, acceptance criteria, and background")
    ] = None,
    source_id: Annotated[Optional[str], typer.Option(help="External source ID")] = None,
    source: Annotated[Optional[str], typer.Option(help="Source type")] = None,
    next_action: Annotated[
        Optional[str], typer.Option(help="Next action to take")
    ] = None,
) -> None:
    """Update task fields."""
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        task = db.update_task(
            resolved_id,
            title=title,
            description=description,
            source_id=source_id,
            source=source,
            next_action=next_action,
        )
    typer.echo(f"Updated: {_short_id(task.id)}  {task.title}")
    if description is not None:
        typer.echo(f"  description: {task.description}")
    if source_id is not None:
        typer.echo(f"  source_id: {task.source_id}")
    if source is not None:
        typer.echo(f"  source: {task.source}")
    if next_action is not None:
        typer.echo(f"  next: {task.next_action}")


@app.command()
def delete(task_id: str) -> None:
    """Delete a task and its progress logs."""
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        task = db.delete_task(resolved_id)
    typer.echo(f"Deleted: {_short_id(task.id)}  {task.title}")


@app.command()
def rank(
    task_id: str,
    after: Annotated[
        Optional[str], typer.Option(help="Place after the specified task")
    ] = None,
) -> None:
    """Change task display order. Moves to top if no --after specified."""
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        after_id = _resolve_id(db, after) if after else None
        task = db.rank_task(resolved_id, after_id=after_id)
    if after_id:
        typer.echo(
            f"Ranked: {_short_id(task.id)} after {_short_id(after_id)}  {task.title}"
        )
    else:
        typer.echo(f"Ranked: {_short_id(task.id)} → top  {task.title}")


@app.command()
def status(
    task_id: str,
    new_status: str,
) -> None:
    """Change a task's status."""
    parsed_status = _parse_status(new_status)
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        task = db.update_status(resolved_id, parsed_status)
    typer.echo(f"{_short_id(task.id)}  {task.status.value}  {task.title}")


@app.command()
def log(
    task_id: str,
    summary: Annotated[str, typer.Option(help="Summary of what was done")],
    details: Annotated[
        Optional[str], typer.Option(help="Detailed changes (files, etc.)")
    ] = None,
    remaining: Annotated[
        Optional[str], typer.Option(help="Remaining work or blockers")
    ] = None,
    next_action: Annotated[
        Optional[str], typer.Option(help="Next action (also updates the task)")
    ] = None,
) -> None:
    """Record a progress log entry."""
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        entry = db.add_log(
            resolved_id, summary=summary, details=details, remaining=remaining
        )
        if next_action is not None:
            db.update_task(resolved_id, next_action=next_action)
    typer.echo(f"Logged: {entry.summary}")
    if entry.details:
        typer.echo(f"  details: {entry.details}")
    if entry.remaining:
        typer.echo(f"  remaining: {entry.remaining}")
    if next_action is not None:
        typer.echo(f"  next: {next_action}")


@app.command("log-update")
def log_update(
    log_id: str,
    summary: Annotated[
        Optional[str], typer.Option(help="Summary of what was done")
    ] = None,
    details: Annotated[
        Optional[str], typer.Option(help="Detailed changes (files, etc.)")
    ] = None,
    remaining: Annotated[
        Optional[str], typer.Option(help="Remaining work or blockers")
    ] = None,
) -> None:
    """Update an existing progress log entry.

    Pass an empty string to clear ``--details`` or ``--remaining``.
    """
    with _get_db() as db:
        resolved_id = _resolve_log_id(db, log_id)
        entry = db.update_log(
            resolved_id, summary=summary, details=details, remaining=remaining
        )
    typer.echo(f"Updated log: {_short_id(entry.id)}  {entry.summary}")
    if entry.details:
        typer.echo(f"  details: {entry.details}")
    if entry.remaining:
        typer.echo(f"  remaining: {entry.remaining}")


@app.command("log-delete")
def log_delete(log_id: str) -> None:
    """Delete a progress log entry."""
    with _get_db() as db:
        resolved_id = _resolve_log_id(db, log_id)
        entry = db.delete_log(resolved_id)
    typer.echo(f"Deleted log: {_short_id(entry.id)}  {entry.summary}")


@app.command()
def show(task_id: str) -> None:
    """Show task details and progress logs."""
    with _get_db() as db:
        resolved_id = _resolve_id(db, task_id)
        task = db.get_task(resolved_id)
        if task is None:
            typer.echo(f"Task {task_id} not found")
            raise typer.Exit(1)
        logs = db.get_logs(resolved_id)
        child_tasks = db.list_tasks(parent_id=task.id)

    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    if task.description:
        typer.echo(f"  description: {task.description}")
    typer.echo(f"  status: {task.status.value}")
    if task.source_id:
        typer.echo(f"  source_id: {task.source_id}")
    if task.source:
        typer.echo(f"  source: {task.source}")
    if task.parent_id:
        typer.echo(f"  parent: {_short_id(task.parent_id)}")
    if task.next_action:
        typer.echo(f"  next: {task.next_action}")
    typer.echo(f"  created: {task.created_at}")
    if child_tasks:
        typer.echo("\nChildren:")
        for child in child_tasks:
            _print_task_line(child, "  ")

    typer.echo("")
    if logs:
        typer.echo("Progress:")
        for entry in logs:
            typer.echo(
                f"  {_short_id(entry.id)}  [{entry.created_at[:16]}] {entry.summary}"
            )
            if entry.details:
                typer.echo(f"    details: {entry.details}")
            if entry.remaining:
                typer.echo(f"    remaining: {entry.remaining}")
    else:
        typer.echo("Progress: (none)")


@app.command()
def board(
    status: Annotated[
        Optional[str], typer.Option(help="Comma-separated statuses")
    ] = None,
    all_tasks: Annotated[
        bool, typer.Option("--all", help="Include all done tasks")
    ] = False,
) -> None:
    """Display tasks in a kanban board layout."""
    from rich.console import Console
    from rich.text import Text

    statuses = [_parse_status(s.strip()) for s in status.split(",")] if status else None
    with _get_db() as db:
        done_since = None if all_tasks else _done_since_cutoff()
        tasks = db.list_tasks(statuses=statuses, done_since=done_since)

    display_statuses = [s for s in TaskStatus if statuses is None or s in statuses]
    by_status: dict[TaskStatus, list[Task]] = {s: [] for s in display_statuses}
    for t in tasks:
        if t.status in by_status:
            by_status[t.status].append(t)

    status_style: dict[TaskStatus, tuple[str, str]] = {
        TaskStatus.TODO: ("TODO", "bright_white"),
        TaskStatus.IN_PROGRESS: ("IN PROGRESS", "yellow"),
        TaskStatus.IN_REVIEW: ("IN REVIEW", "cyan"),
        TaskStatus.DONE: ("DONE", "green"),
    }

    console = Console()

    if not tasks:
        console.print("[dim]No tasks[/]")
        return

    def _render_task_card(t: Task, color: str) -> Text:
        """Render a task as a card-style Text."""
        card = Text()
        card.append(f" {t.title}\n", style=f"bold {color}")
        card.append(f" {_short_id(t.id)}", style="dim")
        if t.source_id:
            card.append(f" {t.source_id}", style="blue")
        card.append("\n")
        if t.next_action:
            card.append(f" → {t.next_action}\n", style="dim italic")
        return card

    from rich.table import Table

    table = Table(
        show_header=False,
        show_edge=False,
        show_lines=False,
        expand=True,
        padding=(0, 1),
        pad_edge=False,
    )
    for s in display_statuses:
        _, color = status_style[s]
        table.add_column(ratio=1, style=color, overflow="fold")

    header_row: list[Text] = []
    for s in display_statuses:
        label, color = status_style[s]
        count = len(by_status[s])
        h = Text()
        h.append(f" {label}", style=f"bold {color}")
        h.append(f" ({count})", style="dim")
        header_row.append(h)
    table.add_row(*header_row)

    sep_row: list[Text] = []
    for s in display_statuses:
        _, color = status_style[s]
        sep_row.append(Text(" ─" * 8, style=f"dim {color}"))
    table.add_row(*sep_row)

    max_rows = max((len(v) for v in by_status.values()), default=0)
    for i in range(max_rows):
        row: list[Text | str] = []
        for s in display_statuses:
            col_tasks = by_status[s]
            if i < len(col_tasks):
                _, color = status_style[s]
                row.append(_render_task_card(col_tasks[i], color))
            else:
                row.append("")
        table.add_row(*row)

    console.print(table)


def _resolve_id(db: TaskDB, partial_id: str) -> str:
    """Resolve a partial ID to a full task ID."""
    try:
        return db.resolve_id(partial_id)
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(1)  # noqa: B904


def _resolve_log_id(db: TaskDB, partial_id: str) -> str:
    """Resolve a partial ID to a full progress log ID."""
    try:
        return db.resolve_log_id(partial_id)
    except ValueError as e:
        typer.echo(str(e))
        raise typer.Exit(1)  # noqa: B904
