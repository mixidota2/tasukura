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
    result = runner.invoke(app, ["add", "テスト実装"])
    assert result.exit_code == 0
    assert "テスト実装" in result.stdout


def test_add_task_with_jira():
    result = runner.invoke(app, ["add", "JIRA連携", "--jira", "PROJ-123"])
    assert result.exit_code == 0
    assert "PROJ-123" in result.stdout


def test_list_tasks():
    runner.invoke(app, ["add", "タスク1"])
    runner.invoke(app, ["add", "タスク2"])
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "タスク1" in result.stdout
    assert "タスク2" in result.stdout


def test_status_change():
    result = runner.invoke(app, ["add", "タスク"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["status", task_id, "in_progress"])
    assert result.exit_code == 0
    assert "in_progress" in result.stdout


def test_log_progress():
    result = runner.invoke(app, ["add", "タスク"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["log", task_id, "--summary", "APIを実装した", "--details", "lib/api.py追加", "--remaining", "テスト"])
    assert result.exit_code == 0
    assert "APIを実装した" in result.stdout


def test_show_task():
    result = runner.invoke(app, ["add", "タスク"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "作業1"])
    result = runner.invoke(app, ["show", task_id])
    assert result.exit_code == 0
    assert "タスク" in result.stdout
    assert "作業1" in result.stdout


def test_daily():
    result = runner.invoke(app, ["add", "タスク"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "今日の作業"])
    result = runner.invoke(app, ["daily"])
    assert result.exit_code == 0
    assert "今日の作業" in result.stdout


def test_jira_report():
    result = runner.invoke(app, ["add", "JIRA付き", "--jira", "PROJ-1"])
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
