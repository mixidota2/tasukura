import os
import tempfile

import pytest
from typer.testing import CliRunner

from tk.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch: pytest.MonkeyPatch):
    """全テストで一時DBを使用する."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("TK_DB_PATH", path)
    yield path
    os.unlink(path)


def test_add_task():
    result = runner.invoke(app, ["add", "テスト実装", "--description", "テストの実装を行う"])
    assert result.exit_code == 0
    assert "テスト実装" in result.stdout
    assert "テストの実装を行う" in result.stdout


def test_add_task_with_jira():
    result = runner.invoke(app, ["add", "JIRA連携", "--description", "JIRA連携タスクの説明", "--jira", "PROJ-123"])
    assert result.exit_code == 0
    assert "PROJ-123" in result.stdout


def test_add_task_requires_description():
    result = runner.invoke(app, ["add", "タスク名だけ"])
    assert result.exit_code != 0


def test_add_task_with_parent():
    result = runner.invoke(app, ["add", "親タスク", "--description", "親の説明"])
    parent_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["add", "子タスク", "--description", "子の説明", "--parent", parent_id])
    assert result.exit_code == 0
    assert "parent:" in result.stdout


def test_add_task_with_next_action():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明", "--next-action", "まずこれをやる"])
    assert result.exit_code == 0
    assert "まずこれをやる" in result.stdout


def test_list_tasks():
    runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    runner.invoke(app, ["add", "タスク2", "--description", "説明2"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "タスク1" in result.stdout
    assert "タスク2" in result.stdout


def test_list_tasks_flat():
    runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    result = runner.invoke(app, ["list", "--flat"])
    assert result.exit_code == 0
    assert "タスク1" in result.stdout


def test_list_tasks_tree_with_children():
    result = runner.invoke(app, ["add", "親", "--description", "親の説明"])
    parent_id = _extract_id(result.stdout)
    runner.invoke(app, ["add", "子", "--description", "子の説明", "--parent", parent_id])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "親" in result.stdout
    assert "子" in result.stdout


def test_list_next_action_display():
    runner.invoke(app, ["add", "タスク", "--description", "説明", "--next-action", "次はこれ"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "-> 次はこれ" in result.stdout


def test_status_change():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["status", task_id, "in_progress"])
    assert result.exit_code == 0
    assert "in_progress" in result.stdout


def test_update_task():
    result = runner.invoke(app, ["add", "タスク", "--description", "元の説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["update", task_id, "--description", "新しい説明"])
    assert result.exit_code == 0
    assert "新しい説明" in result.stdout


def test_update_next_action():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["update", task_id, "--next-action", "次のアクション"])
    assert result.exit_code == 0
    assert "次のアクション" in result.stdout


def test_log_progress():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["log", task_id, "--summary", "APIを実装した", "--details", "lib/api.py追加", "--remaining", "テスト"])
    assert result.exit_code == 0
    assert "APIを実装した" in result.stdout


def test_log_with_next_action():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["log", task_id, "--summary", "実装した", "--details", "詳細", "--next-action", "テストを書く"])
    assert result.exit_code == 0
    assert "テストを書く" in result.stdout
    # タスク本体のnext_actionも更新されていることを確認
    result = runner.invoke(app, ["show", task_id])
    assert "テストを書く" in result.stdout


def test_show_task():
    result = runner.invoke(app, ["add", "タスク", "--description", "タスクの詳細説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "作業1"])
    result = runner.invoke(app, ["show", task_id])
    assert result.exit_code == 0
    assert "タスク" in result.stdout
    assert "タスクの詳細説明" in result.stdout
    assert "作業1" in result.stdout


def test_show_task_with_children():
    result = runner.invoke(app, ["add", "親タスク", "--description", "親の説明"])
    parent_id = _extract_id(result.stdout)
    runner.invoke(app, ["add", "子タスク", "--description", "子の説明", "--parent", parent_id])
    result = runner.invoke(app, ["show", parent_id])
    assert result.exit_code == 0
    assert "Children:" in result.stdout
    assert "子タスク" in result.stdout


def test_daily():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "今日の作業"])
    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    assert "今日の作業" in result.stdout


def test_jira_report():
    result = runner.invoke(app, ["add", "JIRA付き", "--description", "説明", "--jira", "PROJ-1"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "実装完了"])
    result = runner.invoke(app, ["jira-report"])
    assert result.exit_code == 0
    assert "PROJ-1" in result.stdout
    assert "実装完了" in result.stdout


def _extract_id(output: str) -> str:
    """CLIの出力からタスクIDを抽出する."""
    for line in output.strip().split("\n"):
        if "ID:" in line:
            return line.split("ID:")[1].strip().split()[0]
    msg = f"ID not found in output: {output}"
    raise ValueError(msg)
