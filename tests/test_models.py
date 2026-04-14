from tasukura.models import Task, ProgressLog, TaskStatus


def test_task_creation():
    task = Task.new(
        title="テスト実装",
        description="テストの実装を行う",
        source_id="PROJ-123",
        source="jira",
    )
    assert task.title == "テスト実装"
    assert task.description == "テストの実装を行う"
    assert task.status == TaskStatus.TODO
    assert task.source_id == "PROJ-123"
    assert task.source == "jira"
    assert task.parent_id is None
    assert task.next_action is None
    assert task.id  # ULIDが生成されている


def test_task_creation_with_parent_and_next_action():
    task = Task.new(
        title="子タスク",
        description="子タスクの説明",
        parent_id="01PARENT",
        next_action="まずこれをやる",
    )
    assert task.parent_id == "01PARENT"
    assert task.next_action == "まずこれをやる"


def test_task_creation_without_source():
    task = Task.new(title="ローカルタスク", description="ローカルでやるタスク")
    assert task.source_id is None
    assert task.source is None


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
