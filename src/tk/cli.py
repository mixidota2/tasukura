"""tk - ローカルタスク管理CLI."""

from __future__ import annotations

import os
from typing import Annotated, Optional

import typer

from tk.db import TaskDB
from tk.models import TaskStatus

app = typer.Typer(help="tk - ローカルタスク管理CLI")


def _get_db() -> TaskDB:
    """DB接続を取得する。TK_DB_PATH環境変数でパスを上書き可能."""
    db_path = os.environ.get("TK_DB_PATH")
    return TaskDB(db_path)


def _short_id(task_id: str) -> str:
    """IDの先頭8文字を表示用に返す."""
    return task_id[:8]


@app.command()
def add(
    title: str,
    jira: Annotated[Optional[str], typer.Option(help="JIRAチケットキー (例: PROJ-123)")] = None,
) -> None:
    """タスクを追加する."""
    db = _get_db()
    task = db.add_task(title, jira_key=jira)
    db.close()
    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    typer.echo(f"  status: {task.status.value}")
    if task.jira_key:
        typer.echo(f"  jira: {task.jira_key}")


@app.command("list")
def list_tasks(
    status: Annotated[Optional[str], typer.Option(help="カンマ区切りのステータス (例: todo,in_progress)")] = None,
    jira_only: Annotated[bool, typer.Option("--jira-only", help="JIRA連携タスクのみ")] = False,
) -> None:
    """タスク一覧を表示する."""
    db = _get_db()
    statuses = [TaskStatus(s.strip()) for s in status.split(",")] if status else None
    tasks = db.list_tasks(statuses=statuses, jira_only=jira_only)
    db.close()
    if not tasks:
        typer.echo("タスクなし")
        return
    for t in tasks:
        jira = f" [{t.jira_key}]" if t.jira_key else ""
        typer.echo(f"{_short_id(t.id)}  {t.status.value:<12} {t.title}{jira}")


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
) -> None:
    """進捗ログを記録する."""
    db = _get_db()
    resolved_id = _resolve_id(db, task_id)
    entry = db.add_log(resolved_id, summary=summary, details=details, remaining=remaining)
    db.close()
    typer.echo(f"Logged: {entry.summary}")
    if entry.details:
        typer.echo(f"  details: {entry.details}")
    if entry.remaining:
        typer.echo(f"  remaining: {entry.remaining}")


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
    db.close()

    typer.echo(f"ID: {task.id}")
    typer.echo(f"  title: {task.title}")
    typer.echo(f"  status: {task.status.value}")
    if task.jira_key:
        typer.echo(f"  jira: {task.jira_key}")
    typer.echo(f"  created: {task.created_at}")
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
