import os
import tempfile

import pytest

from tk.db import TaskDB
from tk.models import TaskStatus


@pytest.fixture
def db():
    """テスト用の一時DBを作成する."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = TaskDB(path)
    yield database
    database.close()
    os.unlink(path)


def test_add_and_get_task(db: TaskDB):
    task = db.add_task("テスト実装", jira_key="PROJ-123")
    fetched = db.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "テスト実装"
    assert fetched.jira_key == "PROJ-123"
    assert fetched.status == TaskStatus.TODO


def test_list_tasks_by_status(db: TaskDB):
    db.add_task("タスク1")
    t2 = db.add_task("タスク2")
    db.update_status(t2.id, TaskStatus.IN_PROGRESS)

    todo_tasks = db.list_tasks(statuses=[TaskStatus.TODO])
    assert len(todo_tasks) == 1
    assert todo_tasks[0].title == "タスク1"

    in_progress = db.list_tasks(statuses=[TaskStatus.IN_PROGRESS])
    assert len(in_progress) == 1
    assert in_progress[0].title == "タスク2"


def test_list_tasks_all(db: TaskDB):
    db.add_task("タスク1")
    db.add_task("タスク2")
    all_tasks = db.list_tasks()
    assert len(all_tasks) == 2


def test_list_tasks_jira_only(db: TaskDB):
    db.add_task("ローカル")
    db.add_task("JIRA付き", jira_key="PROJ-1")
    jira_tasks = db.list_tasks(jira_only=True)
    assert len(jira_tasks) == 1
    assert jira_tasks[0].jira_key == "PROJ-1"


def test_update_status(db: TaskDB):
    task = db.add_task("タスク")
    db.update_status(task.id, TaskStatus.DONE)
    updated = db.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.DONE


def test_add_and_get_logs(db: TaskDB):
    task = db.add_task("タスク")
    db.add_log(task.id, summary="APIを実装", details="lib/api.py", remaining="テスト")
    db.add_log(task.id, summary="テスト追加")

    logs = db.get_logs(task.id)
    assert len(logs) == 2
    assert logs[0].summary == "APIを実装"
    assert logs[0].details == "lib/api.py"
    assert logs[0].remaining == "テスト"
    assert logs[1].summary == "テスト追加"


def test_daily_logs(db: TaskDB):
    t1 = db.add_task("タスク1")
    t2 = db.add_task("タスク2")
    db.add_log(t1.id, summary="作業1")
    db.add_log(t2.id, summary="作業2")

    # 今日の日付で取得（テスト実行日）
    daily = db.get_daily_logs()
    assert len(daily) == 2


def test_get_task_not_found(db: TaskDB):
    assert db.get_task("nonexistent") is None


def test_update_status_not_found(db: TaskDB):
    with pytest.raises(ValueError, match="not found"):
        db.update_status("nonexistent", TaskStatus.DONE)
