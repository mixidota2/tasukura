import os
import tempfile

import pytest

from tasukura.db import TaskDB
from tasukura.models import TaskStatus


@pytest.fixture
def db():
    """テスト用の一時DBを作成する."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    database = TaskDB(path)
    yield database
    database.close()
    os.unlink(path)


def test_context_manager():
    """TaskDBはコンテキストマネージャとして使える."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with TaskDB(path) as database:
        task = database.add_task("テスト", description="説明")
        assert task.title == "テスト"
    # closeされた後のDBファイルは残っている
    os.unlink(path)


def test_db_file_permissions():
    """DBファイルはowner read/writeのみのパーミッションで作成される."""
    import stat

    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, "sub", "tasks.db")
        database = TaskDB(db_path)
        database.close()
        file_mode = os.stat(db_path).st_mode
        assert file_mode & stat.S_IRWXO == 0, "Others should have no access"
        assert file_mode & stat.S_IRWXG == 0, "Group should have no access"


def test_add_and_get_task(db: TaskDB):
    task = db.add_task(
        "テスト実装", description="テストを書く", source_id="PROJ-123", source="jira"
    )
    fetched = db.get_task(task.id)
    assert fetched is not None
    assert fetched.title == "テスト実装"
    assert fetched.description == "テストを書く"
    assert fetched.source_id == "PROJ-123"
    assert fetched.source == "jira"
    assert fetched.status == TaskStatus.TODO


def test_add_task_with_parent(db: TaskDB):
    parent = db.add_task("親タスク", description="親の説明")
    child = db.add_task("子タスク", description="子の説明", parent_id=parent.id)
    assert child.parent_id == parent.id
    fetched = db.get_task(child.id)
    assert fetched is not None
    assert fetched.parent_id == parent.id


def test_add_task_with_next_action(db: TaskDB):
    task = db.add_task("タスク", description="説明", next_action="まずこれをやる")
    assert task.next_action == "まずこれをやる"


def test_list_tasks_by_status(db: TaskDB):
    db.add_task("タスク1", description="タスク1の説明")
    t2 = db.add_task("タスク2", description="タスク2の説明")
    db.update_status(t2.id, TaskStatus.IN_PROGRESS)

    todo_tasks = db.list_tasks(statuses=[TaskStatus.TODO])
    assert len(todo_tasks) == 1
    assert todo_tasks[0].title == "タスク1"

    in_progress = db.list_tasks(statuses=[TaskStatus.IN_PROGRESS])
    assert len(in_progress) == 1
    assert in_progress[0].title == "タスク2"


def test_list_tasks_all(db: TaskDB):
    db.add_task("タスク1", description="説明1")
    db.add_task("タスク2", description="説明2")
    all_tasks = db.list_tasks()
    assert len(all_tasks) == 2


def test_list_tasks_by_source(db: TaskDB):
    db.add_task("ローカル", description="ローカルタスク")
    db.add_task(
        "外部連携", description="外部連携タスク", source_id="PROJ-1", source="jira"
    )
    source_tasks = db.list_tasks(source="jira")
    assert len(source_tasks) == 1
    assert source_tasks[0].source_id == "PROJ-1"


def test_update_status(db: TaskDB):
    task = db.add_task("タスク", description="説明")
    db.update_status(task.id, TaskStatus.DONE)
    updated = db.get_task(task.id)
    assert updated is not None
    assert updated.status == TaskStatus.DONE


def test_update_task(db: TaskDB):
    task = db.add_task("タスク", description="元の説明")
    updated = db.update_task(task.id, description="新しい説明", title="新タスク名")
    assert updated.title == "新タスク名"
    assert updated.description == "新しい説明"


def test_update_task_next_action(db: TaskDB):
    task = db.add_task("タスク", description="説明")
    updated = db.update_task(task.id, next_action="次はテスト")
    assert updated.next_action == "次はテスト"


def test_add_and_get_logs(db: TaskDB):
    task = db.add_task("タスク", description="説明")
    db.add_log(task.id, summary="APIを実装", details="lib/api.py", remaining="テスト")
    db.add_log(task.id, summary="テスト追加")

    logs = db.get_logs(task.id)
    assert len(logs) == 2
    assert logs[0].summary == "APIを実装"
    assert logs[0].details == "lib/api.py"
    assert logs[0].remaining == "テスト"
    assert logs[1].summary == "テスト追加"


def test_get_task_not_found(db: TaskDB):
    assert db.get_task("nonexistent") is None


def test_update_status_not_found(db: TaskDB):
    with pytest.raises(ValueError, match="not found"):
        db.update_status("nonexistent", TaskStatus.DONE)


def test_add_task_auto_position(db: TaskDB):
    """タスク追加時にpositionが自動採番される."""
    t1 = db.add_task("タスク1", description="説明1")
    t2 = db.add_task("タスク2", description="説明2")
    t3 = db.add_task("タスク3", description="説明3")
    assert t1.position < t2.position < t3.position


def test_list_tasks_ordered_by_position(db: TaskDB):
    """list_tasksはposition順で返す."""
    db.add_task("タスク1", description="説明1")
    db.add_task("タスク2", description="説明2")
    db.add_task("タスク3", description="説明3")
    tasks = db.list_tasks()
    assert [t.title for t in tasks] == ["タスク1", "タスク2", "タスク3"]


def test_rank_task_to_top(db: TaskDB):
    """rank_taskで最上位に移動できる."""
    db.add_task("タスク1", description="説明1")
    db.add_task("タスク2", description="説明2")
    t3 = db.add_task("タスク3", description="説明3")
    db.rank_task(t3.id)  # タスク3を最上位に
    tasks = db.list_tasks()
    assert [t.title for t in tasks] == ["タスク3", "タスク1", "タスク2"]


def test_rank_task_after(db: TaskDB):
    """rank_taskで指定タスクの後ろに配置できる."""
    t1 = db.add_task("タスク1", description="説明1")
    db.add_task("タスク2", description="説明2")
    t3 = db.add_task("タスク3", description="説明3")
    db.rank_task(t3.id, after_id=t1.id)  # タスク3をタスク1の後ろに
    tasks = db.list_tasks()
    assert [t.title for t in tasks] == ["タスク1", "タスク3", "タスク2"]


def test_delete_task(db: TaskDB):
    """タスクを削除できる."""
    task = db.add_task("削除対象", description="説明")
    deleted = db.delete_task(task.id)
    assert deleted.id == task.id
    assert deleted.title == "削除対象"
    assert db.get_task(task.id) is None


def test_delete_task_with_logs(db: TaskDB):
    """タスクと関連するprogress_logsを一緒に削除できる."""
    task = db.add_task("ログ付きタスク", description="説明")
    db.add_log(task.id, summary="進捗1")
    db.add_log(task.id, summary="進捗2")
    assert len(db.get_logs(task.id)) == 2
    db.delete_task(task.id)
    assert db.get_task(task.id) is None
    assert db.get_logs(task.id) == []


def test_delete_task_not_found(db: TaskDB):
    """存在しないタスクの削除はValueErrorになる."""
    with pytest.raises(ValueError, match="not found"):
        db.delete_task("nonexistent")


def test_add_task_with_position(db: TaskDB):
    """position指定でタスクを追加できる."""
    db.add_task("タスク1", description="説明1")
    db.add_task("タスク先頭", description="説明", position=-1)
    tasks = db.list_tasks()
    assert tasks[0].title == "タスク先頭"
