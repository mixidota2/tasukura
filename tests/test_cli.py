import os
import tempfile

import pytest
from typer.testing import CliRunner

import tasukura.cli as cli_module
from tasukura.cli import app

runner = CliRunner()


@pytest.fixture(autouse=True)
def tmp_db(monkeypatch: pytest.MonkeyPatch):
    """全テストで一時DBを使用する."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    monkeypatch.setenv("TK_DB_PATH", path)
    # 設定キャッシュをリセットして環境変数を反映させる
    cli_module._config = None
    yield path
    cli_module._config = None
    os.unlink(path)


def test_add_task():
    result = runner.invoke(
        app, ["add", "テスト実装", "--description", "テストの実装を行う"]
    )
    assert result.exit_code == 0
    assert "テスト実装" in result.stdout
    assert "テストの実装を行う" in result.stdout


def test_add_task_with_source():
    result = runner.invoke(
        app,
        [
            "add",
            "外部連携",
            "--description",
            "外部連携タスクの説明",
            "--source-id",
            "PROJ-123",
            "--source",
            "jira",
        ],
    )
    assert result.exit_code == 0
    assert "PROJ-123" in result.stdout


def test_add_task_requires_description():
    result = runner.invoke(app, ["add", "タスク名だけ"])
    assert result.exit_code != 0


def test_add_task_with_parent():
    result = runner.invoke(app, ["add", "親タスク", "--description", "親の説明"])
    parent_id = _extract_id(result.stdout)
    result = runner.invoke(
        app, ["add", "子タスク", "--description", "子の説明", "--parent", parent_id]
    )
    assert result.exit_code == 0
    assert "parent:" in result.stdout


def test_add_task_with_next_action():
    result = runner.invoke(
        app,
        ["add", "タスク", "--description", "説明", "--next-action", "まずこれをやる"],
    )
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
    runner.invoke(
        app, ["add", "子", "--description", "子の説明", "--parent", parent_id]
    )
    result = runner.invoke(app, ["list"])
    assert result.exit_code == 0
    assert "親" in result.stdout
    assert "子" in result.stdout


def test_list_next_action_display():
    runner.invoke(
        app, ["add", "タスク", "--description", "説明", "--next-action", "次はこれ"]
    )
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
    result = runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "APIを実装した",
            "--details",
            "lib/api.py追加",
            "--remaining",
            "テスト",
        ],
    )
    assert result.exit_code == 0
    assert "APIを実装した" in result.stdout


def test_log_with_next_action():
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "実装した",
            "--details",
            "詳細",
            "--next-action",
            "テストを書く",
        ],
    )
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
    runner.invoke(
        app, ["add", "子タスク", "--description", "子の説明", "--parent", parent_id]
    )
    result = runner.invoke(app, ["show", parent_id])
    assert result.exit_code == 0
    assert "Children:" in result.stdout
    assert "子タスク" in result.stdout


def test_delete_task():
    result = runner.invoke(app, ["add", "削除対象", "--description", "削除するタスク"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["delete", task_id])
    assert result.exit_code == 0
    assert "Deleted:" in result.stdout
    assert "削除対象" in result.stdout
    # listに表示されないことを確認
    result = runner.invoke(app, ["list"])
    assert "削除対象" not in result.stdout


def test_delete_task_with_logs():
    result = runner.invoke(
        app, ["add", "ログ付き削除", "--description", "ログ付きタスクの削除"]
    )
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "進捗メモ"])
    # showでログが見えることを確認
    result = runner.invoke(app, ["show", task_id])
    assert "進捗メモ" in result.stdout
    # 削除
    result = runner.invoke(app, ["delete", task_id])
    assert result.exit_code == 0
    assert "Deleted:" in result.stdout
    # listに表示されないことを確認
    result = runner.invoke(app, ["list"])
    assert "ログ付き削除" not in result.stdout


def test_rank_to_top():
    runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    runner.invoke(app, ["add", "タスク2", "--description", "説明2"])
    result3 = runner.invoke(app, ["add", "タスク3", "--description", "説明3"])
    task3_id = _extract_id(result3.stdout)
    result = runner.invoke(app, ["rank", task3_id])
    assert result.exit_code == 0
    assert "→ top" in result.stdout
    # listで先頭に来ていることを確認
    result = runner.invoke(app, ["list", "--flat"])
    lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
    assert "タスク3" in lines[0]


def test_rank_after():
    result1 = runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    task1_id = _extract_id(result1.stdout)
    runner.invoke(app, ["add", "タスク2", "--description", "説明2"])
    result3 = runner.invoke(app, ["add", "タスク3", "--description", "説明3"])
    task3_id = _extract_id(result3.stdout)
    result = runner.invoke(app, ["rank", task3_id, "--after", task1_id])
    assert result.exit_code == 0
    assert "after" in result.stdout
    # listでタスク1の次にタスク3が来ていることを確認
    result = runner.invoke(app, ["list", "--flat"])
    lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
    titles = [line.split("  ")[-1].strip() for line in lines]
    # タスク1, タスク3, タスク2の順
    idx1 = next(i for i, t in enumerate(titles) if "タスク1" in t)
    idx3 = next(i for i, t in enumerate(titles) if "タスク3" in t)
    idx2 = next(i for i, t in enumerate(titles) if "タスク2" in t)
    assert idx1 < idx3 < idx2


def test_add_with_top():
    runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    runner.invoke(app, ["add", "先頭タスク", "--description", "説明", "--top"])
    result = runner.invoke(app, ["list", "--flat"])
    lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
    assert "先頭タスク" in lines[0]


def test_add_with_after():
    result1 = runner.invoke(app, ["add", "タスク1", "--description", "説明1"])
    task1_id = _extract_id(result1.stdout)
    runner.invoke(app, ["add", "タスク2", "--description", "説明2"])
    runner.invoke(
        app, ["add", "挿入タスク", "--description", "説明", "--after", task1_id]
    )
    result = runner.invoke(app, ["list", "--flat"])
    lines = [line for line in result.stdout.strip().split("\n") if line.strip()]
    # タスク1, 挿入タスク, タスク2の順
    idx1 = next(i for i, line in enumerate(lines) if "タスク1" in line)
    idx_ins = next(i for i, line in enumerate(lines) if "挿入タスク" in line)
    idx2 = next(i for i, line in enumerate(lines) if "タスク2" in line)
    assert idx1 < idx_ins < idx2


def test_invalid_status_in_status_command():
    """不正なステータスでエラーメッセージを表示する."""
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["status", task_id, "invalid_status"])
    assert result.exit_code == 1
    assert "Invalid status" in result.stdout
    assert "invalid_status" in result.stdout


def test_invalid_status_in_list_command():
    """listの--statusに不正な値でエラーメッセージを表示する."""
    result = runner.invoke(app, ["list", "--status", "bad"])
    assert result.exit_code == 1
    assert "Invalid status" in result.stdout


def test_invalid_status_in_board_command():
    """boardの--statusに不正な値でエラーメッセージを表示する."""
    result = runner.invoke(app, ["board", "--status", "bad"])
    assert result.exit_code == 1
    assert "Invalid status" in result.stdout


def test_board():
    runner.invoke(app, ["add", "タスクA", "--description", "説明A"])
    result = runner.invoke(app, ["board"])
    assert result.exit_code == 0
    assert "TODO" in result.stdout
    assert "タスクA" in result.stdout


def _extract_id(output: str) -> str:
    """CLIの出力からタスクIDを抽出する."""
    for line in output.strip().split("\n"):
        if "ID:" in line:
            return line.split("ID:")[1].strip().split()[0]
    msg = f"ID not found in output: {output}"
    raise ValueError(msg)
