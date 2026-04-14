"""tk - ローカルタスク管理CLI."""

from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

import typer

from tasukura.config import TkConfig
from tasukura.db import TaskDB
from tasukura.models import Task, TaskStatus

app = typer.Typer(help="tk - ローカルタスク管理CLI")

_config: TkConfig | None = None


def _get_config() -> TkConfig:
    """設定を取得する（シングルトン）."""
    global _config  # noqa: PLW0603
    if _config is None:
        _config = TkConfig.load()
    return _config


def _get_db() -> TaskDB:
    """DB接続を取得する."""
    return TaskDB(_get_config().db_path)


def _done_since_cutoff() -> str:
    """done タスクの表示期限（ISO8601）を返す."""
    config = _get_config()
    cutoff = datetime.now(timezone.utc) - timedelta(days=config.done_retention_days)
    return cutoff.isoformat()


def _short_id(task_id: str) -> str:
    """IDの先頭12文字を表示用に返す.

    ULIDの先頭10文字はタイムスタンプ（ミリ秒精度）のため、
    同時刻に作成されたタスクでも識別できるようランダム部2文字を含む12文字を使用する。
    """
    return task_id[:12]


@app.command()
def add(
    title: str,
    description: Annotated[str, typer.Option(help="タスクのゴール・完了条件・背景")],
    jira: Annotated[Optional[str], typer.Option(help="JIRAチケットキー (例: PROJ-123)")] = None,
    parent: Annotated[Optional[str], typer.Option(help="親タスクID")] = None,
    next_action: Annotated[Optional[str], typer.Option(help="次にやるべきこと")] = None,
    top: Annotated[bool, typer.Option("--top", help="最上位に追加")] = False,
    after: Annotated[Optional[str], typer.Option(help="指定タスクの後ろに追加")] = None,
) -> None:
    """タスクを追加する."""
    db = _get_db()
    parent_id = _resolve_id(db, parent) if parent else None
    position: int | None = None
    if top:
        position = db.get_top_position()
    elif after:
        after_id = _resolve_id(db, after)
        position = db.get_position_after(after_id)
    task = db.add_task(title, description=description, jira_key=jira, parent_id=parent_id, next_action=next_action, position=position)
    db.close()
    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    typer.echo(f"  description: {task.description}")
    typer.echo(f"  status: {task.status.value}")
    if task.jira_key:
        typer.echo(f"  jira: {task.jira_key}")
    if task.parent_id:
        typer.echo(f"  parent: {_short_id(task.parent_id)}")
    if task.next_action:
        typer.echo(f"  next: {task.next_action}")


@app.command("list")
def list_tasks(
    status: Annotated[Optional[str], typer.Option(help="カンマ区切りのステータス (例: todo,in_progress)")] = None,
    jira_only: Annotated[bool, typer.Option("--jira-only", help="JIRA連携タスクのみ")] = False,
    flat: Annotated[bool, typer.Option("--flat", help="フラット表示（ツリーなし）")] = False,
    all_tasks: Annotated[bool, typer.Option("--all", help="完了済みタスクもすべて表示")] = False,
) -> None:
    """タスク一覧を表示する。デフォルトはツリー表示."""
    db = _get_db()
    statuses = [TaskStatus(s.strip()) for s in status.split(",")] if status else None
    done_since = None if all_tasks else _done_since_cutoff()
    tasks = db.list_tasks(statuses=statuses, jira_only=jira_only, done_since=done_since)
    db.close()
    if not tasks:
        typer.echo("タスクなし")
        return
    if flat:
        for t in tasks:
            _print_task_line(t)
    else:
        _print_task_tree(tasks)


def _print_task_line(t: Task, indent: str = "") -> None:
    """タスク1行を表示する."""
    jira = f" [{t.jira_key}]" if t.jira_key else ""
    next_act = f" -> {t.next_action}" if t.next_action else ""
    typer.echo(f"{indent}{_short_id(t.id)}  {t.status.value:<12} {t.title}{jira}{next_act}")


def _print_task_tree(tasks: list[Task]) -> None:
    """タスクをツリー形式で表示する。親なしタスクをルートとして階層表示."""
    children: dict[str | None, list[Task]] = {}
    for t in tasks:
        children.setdefault(t.parent_id, []).append(t)

    def _print_children(parent_id: str | None, indent: str) -> None:
        for child in children.get(parent_id, []):
            _print_task_line(child, indent)
            _print_children(child.id, indent + "  ")

    # ルートタスク（parent_idがNone）を表示
    for t in children.get(None, []):
        _print_task_line(t)
        _print_children(t.id, "  ")

    # parent_idがセットされているが、親がフィルタで除外されたタスクも表示
    displayed_ids = {t.id for t in tasks}
    for t in tasks:
        if t.parent_id is not None and t.parent_id not in displayed_ids:
            _print_task_line(t)


@app.command()
def update(
    task_id: str,
    title: Annotated[Optional[str], typer.Option(help="タスク名")] = None,
    description: Annotated[Optional[str], typer.Option(help="タスクのゴール・完了条件・背景")] = None,
    jira: Annotated[Optional[str], typer.Option(help="JIRAチケットキー")] = None,
    next_action: Annotated[Optional[str], typer.Option(help="次にやるべきこと")] = None,
) -> None:
    """タスクのフィールドを更新する."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    task = db.update_task(resolved_id, title=title, description=description, jira_key=jira, next_action=next_action)
    db.close()
    typer.echo(f"Updated: {_short_id(task.id)}  {task.title}")
    if description is not None:
        typer.echo(f"  description: {task.description}")
    if next_action is not None:
        typer.echo(f"  next: {task.next_action}")


@app.command()
def rank(
    task_id: str,
    after: Annotated[Optional[str], typer.Option(help="指定タスクの後ろに配置")] = None,
) -> None:
    """タスクの表示順序を変更する。引数なしで最上位に移動."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    after_id = _resolve_id(db, after) if after else None
    task = db.rank_task(resolved_id, after_id=after_id)
    db.close()
    if after_id:
        typer.echo(f"Ranked: {_short_id(task.id)} after {_short_id(after_id)}  {task.title}")
    else:
        typer.echo(f"Ranked: {_short_id(task.id)} → top  {task.title}")


@app.command()
def status(
    task_id: str,
    new_status: str,
) -> None:
    """タスクのステータスを変更する."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    task = db.update_status(resolved_id, TaskStatus(new_status))
    db.close()
    typer.echo(f"{_short_id(task.id)}  {task.status.value}  {task.title}")


@app.command()
def log(
    task_id: str,
    summary: Annotated[str, typer.Option(help="やったことの要約")],
    details: Annotated[Optional[str], typer.Option(help="変更ファイル等の詳細")] = None,
    remaining: Annotated[Optional[str], typer.Option(help="残タスク・ブロッカー")] = None,
    next_action: Annotated[Optional[str], typer.Option(help="次にやるべきこと（タスク本体も更新）")] = None,
) -> None:
    """進捗ログを記録する."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    entry = db.add_log(resolved_id, summary=summary, details=details, remaining=remaining)
    if next_action is not None:
        db.update_task(resolved_id, next_action=next_action)
    db.close()
    typer.echo(f"Logged: {entry.summary}")
    if entry.details:
        typer.echo(f"  details: {entry.details}")
    if entry.remaining:
        typer.echo(f"  remaining: {entry.remaining}")
    if next_action is not None:
        typer.echo(f"  next: {next_action}")


@app.command()
def show(task_id: str) -> None:
    """タスクの詳細と進捗ログを表示する."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    task = db.get_task(resolved_id)
    if task is None:
        typer.echo(f"Task {task_id} not found")
        raise typer.Exit(1)
    logs = db.get_logs(resolved_id)
    child_tasks = [t for t in db.list_tasks() if t.parent_id == task.id]
    db.close()

    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    if task.description:
        typer.echo(f"  description: {task.description}")
    typer.echo(f"  status: {task.status.value}")
    if task.jira_key:
        typer.echo(f"  jira: {task.jira_key}")
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
            typer.echo(f"  [{entry.created_at[:16]}] {entry.summary}")
            if entry.details:
                typer.echo(f"    details: {entry.details}")
            if entry.remaining:
                typer.echo(f"    remaining: {entry.remaining}")
    else:
        typer.echo("Progress: (none)")


@app.command()
def daily(
    date: Annotated[Optional[str], typer.Option(help="日付 YYYY-MM-DD（デフォルト: 今日）")] = None,
) -> None:
    """指定日の進捗をまとめて表示する."""
    db = _get_db()
    entries = db.get_daily_logs(date=date)
    db.close()
    if not entries:
        typer.echo("該当日の進捗なし")
        return
    current_task_id = None
    for task, entry in entries:
        if task.id != current_task_id:
            jira = f" [{task.jira_key}]" if task.jira_key else ""
            typer.echo(f"\n{task.title}{jira} ({task.status.value})")
            current_task_id = task.id
        typer.echo(f"  - {entry.summary}")
        if entry.details:
            typer.echo(f"    details: {entry.details}")
        if entry.remaining:
            typer.echo(f"    remaining: {entry.remaining}")


@app.command("jira-report")
def jira_report(
    date: Annotated[Optional[str], typer.Option(help="日付 YYYY-MM-DD（デフォルト: 今日）")] = None,
) -> None:
    """JIRA更新用のレポートを生成する."""
    db = _get_db()
    entries = db.get_daily_logs(date=date)
    db.close()

    # JIRAキー付きのタスクだけ抽出
    jira_entries: dict[str, list[tuple]] = {}
    for task, entry in entries:
        if task.jira_key:
            jira_entries.setdefault(task.jira_key, []).append((task, entry))

    if not jira_entries:
        typer.echo("JIRA連携タスクの進捗なし")
        return

    for jira_key, items in jira_entries.items():
        task = items[0][0]
        typer.echo(f"\n{jira_key}: {task.title}")
        typer.echo(f"  status: {task.status.value}")
        typer.echo("  進捗:")
        for _, entry in items:
            typer.echo(f"    - {entry.summary}")
            if entry.details:
                typer.echo(f"      {entry.details}")
        # 最後のログのremainingを表示
        last_remaining = items[-1][1].remaining
        if last_remaining:
            typer.echo(f"  残タスク: {last_remaining}")


@app.command()
def board(
    status_filter: Annotated[Optional[str], typer.Option("--status", help="カンマ区切りのステータス")] = None,
    all_tasks: Annotated[bool, typer.Option("--all", help="完了済みタスクもすべて表示")] = False,
) -> None:
    """カンバンボード風にタスクを表示する."""
    from rich.console import Console
    from rich.text import Text

    db = _get_db()
    statuses = [TaskStatus(s.strip()) for s in status_filter.split(",")] if status_filter else None
    done_since = None if all_tasks else _done_since_cutoff()
    tasks = db.list_tasks(statuses=statuses, done_since=done_since)
    db.close()

    # ステータスごとにグループ化（position順は list_tasks が保証）
    display_statuses = [s for s in TaskStatus if statuses is None or s in statuses]
    by_status: dict[TaskStatus, list[Task]] = {s: [] for s in display_statuses}
    for t in tasks:
        if t.status in by_status:
            by_status[t.status].append(t)

    # ステータスの色設定
    status_style: dict[TaskStatus, tuple[str, str]] = {
        TaskStatus.TODO: ("TODO", "bright_white"),
        TaskStatus.IN_PROGRESS: ("IN PROGRESS", "yellow"),
        TaskStatus.IN_REVIEW: ("IN REVIEW", "cyan"),
        TaskStatus.DONE: ("DONE", "green"),
    }

    console = Console()

    if not tasks:
        console.print("[dim]タスクなし[/]")
        return

    def _render_task_card(t: Task, color: str) -> Text:
        """タスク1件をカード風のTextに整形する."""
        card = Text()
        card.append(f" {t.title}\n", style=f"bold {color}")
        card.append(f" {_short_id(t.id)}", style="dim")
        if t.jira_key:
            card.append(f" {t.jira_key}", style="blue")
        card.append("\n")
        if t.next_action:
            card.append(f" → {t.next_action}\n", style="dim italic")
        return card

    # 各ステータスの列を構築（テーブルで横並びを強制）
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

    # ヘッダー行
    header_row: list[Text] = []
    for s in display_statuses:
        label, color = status_style[s]
        count = len(by_status[s])
        h = Text()
        h.append(f" {label}", style=f"bold {color}")
        h.append(f" ({count})", style="dim")
        header_row.append(h)
    table.add_row(*header_row)

    # 区切り線
    sep_row: list[Text] = []
    for s in display_statuses:
        _, color = status_style[s]
        sep_row.append(Text(" ─" * 8, style=f"dim {color}"))
    table.add_row(*sep_row)

    # タスク行
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
    """短縮IDから完全なIDを解決する."""
    tasks = db.list_tasks()
    matches = [t for t in tasks if t.id.startswith(partial_id)]
    if len(matches) == 0:
        typer.echo(f"Task not found: {partial_id}")
        raise typer.Exit(1)
    if len(matches) > 1:
        typer.echo(f"Ambiguous ID: {partial_id} (matches {len(matches)} tasks)")
        raise typer.Exit(1)
    return matches[0].id
