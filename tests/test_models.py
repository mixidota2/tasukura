from tasukura.models import (
    Task,
    ProgressLog,
    TaskStatus,
    Record,
    RecordKind,
    RecordStatus,
)


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


def test_record_new_defaults():
    record = Record.new(
        task_id="01ABC",
        kind=RecordKind.DECISION,
        source_log_id="01LOG",
        summary="認証にOIDCを採用",
    )
    assert record.task_id == "01ABC"
    assert record.kind == RecordKind.DECISION
    assert record.source_log_id == "01LOG"
    assert record.summary == "認証にOIDCを採用"
    assert record.status == RecordStatus.ACTIVE
    assert record.details is None
    assert record.supersedes is None
    assert record.resolved_at is None
    assert record.last_verified_at is None
    assert record.created_at == record.updated_at
    assert len(record.id) == 26  # ULID length


def test_record_new_with_optional_fields():
    record = Record.new(
        task_id="01ABC",
        kind=RecordKind.FINDING,
        source_log_id="01LOG",
        summary="Library X stops on Py3.11",
        details="reproduction: ...",
        supersedes="01OLD",
    )
    assert record.details == "reproduction: ..."
    assert record.supersedes == "01OLD"


def test_record_kind_values():
    assert RecordKind.DECISION.value == "decision"
    assert RecordKind.FINDING.value == "finding"
    assert RecordKind.BLOCKER.value == "blocker"
    assert RecordKind.QUESTION.value == "question"
    assert RecordKind.HYPOTHESIS.value == "hypothesis"


def test_record_status_values():
    assert RecordStatus.ACTIVE.value == "active"
    assert RecordStatus.SUPERSEDED.value == "superseded"
    assert RecordStatus.OBSOLETE.value == "obsolete"
    assert RecordStatus.RESOLVED.value == "resolved"


def test_progress_log_next_action_set_optional():
    log = ProgressLog.new(task_id="01TASK", summary="s")
    assert log.next_action_set is None
    log2 = ProgressLog.new(task_id="01TASK", summary="s", next_action_set="次はテスト")
    assert log2.next_action_set == "次はテスト"
