from tk.models import Task, ProgressLog, TaskStatus


def test_task_creation():
    task = Task.new(title="テスト実装", jira_key="PROJ-123")
    assert task.title == "テスト実装"
    assert task.status == TaskStatus.TODO
    assert task.jira_key == "PROJ-123"
    assert task.id  # ULIDが生成されている


def test_task_creation_without_jira():
    task = Task.new(title="ローカルタスク")
    assert task.jira_key is None


def test_progress_log_creation():
    log = ProgressLog.new(
        task_id="01JTEST",
        summary="APIを実装した",
        details="lib/api.py を追加",
        remaining="テスト未実装",
    )
    assert log.summary == "APIを実装した"
    assert log.task_id == "01JTEST"
    assert log.id  # ULIDが生成されている


def test_task_status_values():
    assert TaskStatus.TODO == "todo"
    assert TaskStatus.IN_PROGRESS == "in_progress"
    assert TaskStatus.IN_REVIEW == "in_review"
    assert TaskStatus.DONE == "done"
