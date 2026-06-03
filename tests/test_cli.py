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


def test_update_task_title_still_works():
    result = runner.invoke(app, ["add", "before", "--description", "d"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["update", task_id, "--title", "after"])
    assert result.exit_code == 0
    assert "after" in result.stdout


def test_update_next_action_flag_removed():
    """--next-action は tk update から削除済み."""
    result = runner.invoke(app, ["add", "T1", "--description", "d"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["update", task_id, "--next-action", "blocked"])
    assert result.exit_code != 0


def test_update_description_flag_removed():
    result = runner.invoke(app, ["add", "T1", "--description", "d"])
    task_id = _extract_id(result.stdout)
    result = runner.invoke(app, ["update", task_id, "--description", "blocked"])
    assert result.exit_code != 0


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


def test_log_update():
    """log-updateで個別ログの内容を変更できる."""
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "旧サマリ",
            "--details",
            "旧詳細",
        ],
    )
    log_id = _extract_log_id(runner.invoke(app, ["show", task_id]).stdout)
    result = runner.invoke(
        app,
        ["log-update", log_id, "--summary", "新サマリ", "--details", "新詳細"],
    )
    assert result.exit_code == 0
    assert "新サマリ" in result.stdout
    # showにも反映されている
    show_out = runner.invoke(app, ["show", task_id]).stdout
    assert "新サマリ" in show_out
    assert "新詳細" in show_out
    assert "旧サマリ" not in show_out


def test_log_update_partial():
    """log-updateは指定フィールドのみ更新する."""
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "summary",
            "--details",
            "details",
            "--remaining",
            "remaining",
        ],
    )
    log_id = _extract_log_id(runner.invoke(app, ["show", task_id]).stdout)
    result = runner.invoke(app, ["log-update", log_id, "--remaining", "新remaining"])
    assert result.exit_code == 0
    show_out = runner.invoke(app, ["show", task_id]).stdout
    assert "summary" in show_out
    assert "details" in show_out
    assert "新remaining" in show_out


def test_log_update_not_found():
    """存在しないログIDはエラーになる."""
    result = runner.invoke(app, ["log-update", "zzzzzzzz", "--summary", "x"])
    assert result.exit_code == 1
    assert "Log not found" in result.stdout


def test_log_delete():
    """log-deleteで個別ログを削除できる."""
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "残すログ"])
    runner.invoke(app, ["log", task_id, "--summary", "消すログ"])
    show_out = runner.invoke(app, ["show", task_id]).stdout
    log_id = _extract_log_id_for_summary(show_out, "消すログ")
    result = runner.invoke(app, ["log-delete", log_id])
    assert result.exit_code == 0
    assert "Deleted log:" in result.stdout
    show_out = runner.invoke(app, ["show", task_id]).stdout
    assert "残すログ" in show_out
    assert "消すログ" not in show_out


def test_log_delete_not_found():
    """存在しないログIDの削除はエラー."""
    result = runner.invoke(app, ["log-delete", "zzzzzzzz"])
    assert result.exit_code == 1
    assert "Log not found" in result.stdout


def test_show_displays_log_id():
    """tk showはProgressに短縮ログIDを表示する."""
    result = runner.invoke(app, ["add", "タスク", "--description", "説明"])
    task_id = _extract_id(result.stdout)
    runner.invoke(app, ["log", task_id, "--summary", "作業"])
    show_out = runner.invoke(app, ["show", task_id]).stdout
    # ULIDの先頭が必ず "01" で始まる
    assert "  01" in show_out


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


def _extract_log_id(show_output: str) -> str:
    """tk showの出力から最初の短縮ログIDを抽出する."""
    in_progress = False
    for line in show_output.split("\n"):
        if line.startswith("Recent logs"):
            in_progress = True
            continue
        if in_progress and line.startswith("  01"):
            # 行頭は "  <short_id>  [..."
            return line.strip().split()[0]
    msg = f"Log ID not found in output: {show_output}"
    raise ValueError(msg)


def _extract_log_id_for_summary(show_output: str, summary: str) -> str:
    """tk showの出力から指定summaryに対応する短縮ログIDを抽出する."""
    in_progress = False
    for line in show_output.split("\n"):
        if line.startswith("Recent logs"):
            in_progress = True
            continue
        if in_progress and line.startswith("  01") and summary in line:
            return line.strip().split()[0]
    msg = f"Log ID for summary {summary!r} not found in: {show_output}"
    raise ValueError(msg)


def test_record_add_requires_log_id():
    """--log-id なしでは失敗する (promotion gate)."""
    runner.invoke(app, ["add", "T1", "--description", "d"])
    result = runner.invoke(
        app,
        [
            "record",
            "add",
            "01ANYTASK",
            "--kind",
            "decision",
            "--summary",
            "S",
        ],
    )
    assert result.exit_code != 0


def test_record_add_success():
    add_out = runner.invoke(app, ["add", "T1", "--description", "d"])
    task_id = _extract_id(add_out.stdout)
    log_out = runner.invoke(app, ["log", task_id, "--summary", "raw evidence"])
    assert log_out.exit_code == 0
    log_id = _extract_id(log_out.stdout)  # uses the new "ID:" line printed by tk log

    result = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "認証にOIDCを採用",
        ],
    )
    assert result.exit_code == 0, result.stdout
    assert "認証にOIDCを採用" in result.stdout
    assert "decision" in result.stdout


def test_record_add_invalid_kind():
    add_out = runner.invoke(app, ["add", "T1", "--description", "d"])
    task_id = _extract_id(add_out.stdout)
    log_out = runner.invoke(app, ["log", task_id, "--summary", "l"])
    log_id = _extract_id(log_out.stdout)

    result = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "garbage",
            "--log-id",
            log_id,
            "--summary",
            "S",
        ],
    )
    assert result.exit_code != 0


def test_record_list_empty():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    result = runner.invoke(app, ["record", "list", task_id])
    assert result.exit_code == 0
    assert "No records" in result.stdout


def test_record_list_with_records():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "認証にOIDCを採用",
        ],
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "finding",
            "--log-id",
            log_id,
            "--summary",
            "Library X はPy3.11で停止",
        ],
    )
    result = runner.invoke(app, ["record", "list", task_id])
    assert result.exit_code == 0
    assert "認証にOIDCを採用" in result.stdout
    assert "Library X" in result.stdout


def test_record_list_filter_by_kind():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "decision-only",
        ],
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "finding",
            "--log-id",
            log_id,
            "--summary",
            "finding-only",
        ],
    )
    result = runner.invoke(app, ["record", "list", task_id, "--kind", "decision"])
    assert result.exit_code == 0
    assert "decision-only" in result.stdout
    assert "finding-only" not in result.stdout


def test_record_show_basic():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(
        runner.invoke(app, ["log", task_id, "--summary", "raw"]).stdout
    )
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "認証にOIDCを採用",
            "--details",
            "判断軸: メンテコスト",
        ],
    )
    record_id = _extract_id(add_out.stdout)

    result = runner.invoke(app, ["record", "show", record_id])
    assert result.exit_code == 0, result.stdout
    assert "認証にOIDCを採用" in result.stdout
    assert "判断軸: メンテコスト" in result.stdout
    assert "decision" in result.stdout
    assert "active" in result.stdout
    # Reference back to the source log
    assert log_id[:6] in result.stdout


def test_record_show_partial_id():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "partial-marker",
        ],
    )
    record_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "show", record_id[:8]])
    assert result.exit_code == 0
    assert "partial-marker" in result.stdout


def test_record_show_not_found():
    result = runner.invoke(app, ["record", "show", "01ZZZZZZ"])
    assert result.exit_code != 0


def test_cli_delete_task_with_record_clean_error():
    """tk delete でrecordを持つtaskを消すと、tracebackではなくクリーンなエラーが出る."""
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "blocker-test",
        ],
    )
    result = runner.invoke(app, ["delete", task_id])
    assert result.exit_code != 0
    assert "Cannot delete task" in result.stdout
    assert "Traceback" not in result.stdout


def test_cli_delete_log_referenced_by_record_clean_error():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "blocker-test",
        ],
    )
    result = runner.invoke(app, ["log-delete", log_id])
    assert result.exit_code != 0
    assert "Cannot delete log" in result.stdout
    assert "Traceback" not in result.stdout


def test_record_add_with_supersedes_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    old_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "old-decision",
        ],
    )
    old_id = _extract_id(old_out.stdout)
    new_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "new-decision",
            "--supersedes",
            old_id,
        ],
    )
    assert new_out.exit_code == 0, new_out.stdout
    list_out = runner.invoke(app, ["record", "list", task_id])
    assert "new-decision" in list_out.stdout
    assert "old-decision" not in list_out.stdout
    list_all = runner.invoke(app, ["record", "list", task_id, "--all"])
    assert "old-decision" in list_all.stdout
    assert "[superseded]" in list_all.stdout


def test_record_add_supersedes_partial_id():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    old_id = _extract_id(
        runner.invoke(
            app,
            [
                "record",
                "add",
                task_id,
                "--kind",
                "decision",
                "--log-id",
                log_id,
                "--summary",
                "p-old",
            ],
        ).stdout
    )
    new_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "p-new",
            "--supersedes",
            old_id[:8],
        ],
    )
    assert new_out.exit_code == 0


def test_record_update_summary_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "before-edit",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "update", rec_id, "--summary", "after-edit"])
    assert result.exit_code == 0, result.stdout
    show = runner.invoke(app, ["record", "show", rec_id])
    assert "after-edit" in show.stdout
    assert "before-edit" not in show.stdout


def test_record_update_clear_details():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "S",
            "--details",
            "initial-details",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "update", rec_id, "--details", ""])
    assert result.exit_code == 0
    show = runner.invoke(app, ["record", "show", rec_id])
    assert "initial-details" not in show.stdout


def test_record_update_not_found():
    result = runner.invoke(app, ["record", "update", "01ZZZZZZ", "--summary", "x"])
    assert result.exit_code != 0


def test_record_resolve_blocker_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "blocker",
            "--log-id",
            log_id,
            "--summary",
            "block-it",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "resolve", rec_id])
    assert result.exit_code == 0, result.stdout
    list_default = runner.invoke(app, ["record", "list", task_id])
    assert "block-it" not in list_default.stdout
    list_all = runner.invoke(app, ["record", "list", task_id, "--all"])
    assert "block-it" in list_all.stdout
    assert "[resolved]" in list_all.stdout


def test_record_resolve_non_blocker_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "not-blocker",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "resolve", rec_id])
    assert result.exit_code != 0
    assert "Only blocker" in result.stdout


def test_record_obsolete_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "obs-target",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "obsolete", rec_id])
    assert result.exit_code == 0, result.stdout
    list_default = runner.invoke(app, ["record", "list", task_id])
    assert "obs-target" not in list_default.stdout
    list_all = runner.invoke(app, ["record", "list", task_id, "--all"])
    assert "obs-target" in list_all.stdout
    assert "[obsolete]" in list_all.stdout


def test_record_obsolete_not_found():
    result = runner.invoke(app, ["record", "obsolete", "01ZZZZZZ"])
    assert result.exit_code != 0


def test_record_verify_via_cli():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "l"]).stdout)
    add_out = runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "v-target",
        ],
    )
    rec_id = _extract_id(add_out.stdout)
    result = runner.invoke(app, ["record", "verify", rec_id])
    assert result.exit_code == 0, result.stdout
    show = runner.invoke(app, ["record", "show", rec_id])
    assert "last_verified_at" in show.stdout


def test_record_verify_not_found():
    result = runner.invoke(app, ["record", "verify", "01ZZZZZZ"])
    assert result.exit_code != 0


def test_show_default_lists_active_records_by_kind():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(
        runner.invoke(app, ["log", task_id, "--summary", "evidence"]).stdout
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "dec-1",
        ],
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "blocker",
            "--log-id",
            log_id,
            "--summary",
            "blk-1",
        ],
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "finding",
            "--log-id",
            log_id,
            "--summary",
            "fnd-1",
        ],
    )
    out = runner.invoke(app, ["show", task_id]).stdout
    assert "Active Decisions (1):" in out
    assert "dec-1" in out
    assert "Active Blockers (1):" in out
    assert "blk-1" in out
    assert "Open Findings (1):" in out
    assert "fnd-1" in out


def test_show_empty_sections_say_none():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    out = runner.invoke(app, ["show", task_id]).stdout
    assert "Active Decisions (0):" in out
    assert "(none)" in out


def test_show_recent_logs_default_5():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    for i in range(7):
        runner.invoke(app, ["log", task_id, "--summary", f"log-{i}"])
    out = runner.invoke(app, ["show", task_id]).stdout
    assert "Recent logs (5):" in out
    assert "log-6" in out
    assert "log-2" in out
    assert "log-0" not in out


def test_show_logs_flag_overrides_count():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    for i in range(7):
        runner.invoke(app, ["log", task_id, "--summary", f"log-{i}"])
    out = runner.invoke(app, ["show", task_id, "--logs", "2"]).stdout
    assert "Recent logs (2):" in out
    assert "log-6" in out
    assert "log-5" in out
    assert "log-4" not in out


def test_show_kind_filter_limits_records():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "ev"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "dec-x",
        ],
    )
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "finding",
            "--log-id",
            log_id,
            "--summary",
            "fnd-x",
        ],
    )
    out = runner.invoke(app, ["show", task_id, "--kind", "decision"]).stdout
    assert "dec-x" in out
    assert "fnd-x" not in out


def test_show_full_includes_inactive_records():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "ev"]).stdout)
    rec_id = _extract_id(
        runner.invoke(
            app,
            [
                "record",
                "add",
                task_id,
                "--kind",
                "decision",
                "--log-id",
                log_id,
                "--summary",
                "to-be-obsoleted",
            ],
        ).stdout
    )
    runner.invoke(app, ["record", "obsolete", rec_id])
    default_out = runner.invoke(app, ["show", task_id]).stdout
    assert "to-be-obsoleted" not in default_out
    full_out = runner.invoke(app, ["show", task_id, "--full"]).stdout
    assert "to-be-obsoleted" in full_out
    assert "[obsolete]" in full_out


def test_show_stale_marker_for_old_record():
    """30日以上前に作成され、verify されていないactive record には [stale] が付く."""
    import sqlite3
    from datetime import datetime, timedelta
    from datetime import timezone as _tz

    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "ev"]).stdout)
    runner.invoke(
        app,
        [
            "record",
            "add",
            task_id,
            "--kind",
            "decision",
            "--log-id",
            log_id,
            "--summary",
            "old-dec",
        ],
    )
    db_path = os.environ["TK_DB_PATH"]
    conn = sqlite3.connect(db_path)
    past = (datetime.now(_tz.utc) - timedelta(days=60)).isoformat()
    conn.execute("UPDATE records SET created_at = ?, last_verified_at = NULL", (past,))
    conn.commit()
    conn.close()
    out = runner.invoke(app, ["show", task_id]).stdout
    assert "old-dec" in out
    assert "[stale]" in out


def test_show_active_count_warning():
    """blocker のデフォルト閾値 3 を超えると警告."""
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_id = _extract_id(runner.invoke(app, ["log", task_id, "--summary", "ev"]).stdout)
    for i in range(4):
        runner.invoke(
            app,
            [
                "record",
                "add",
                task_id,
                "--kind",
                "blocker",
                "--log-id",
                log_id,
                "--summary",
                f"blocker-{i}",
            ],
        )
    out = runner.invoke(app, ["show", task_id]).stdout
    assert "Active blockers" in out or "Active Blockers" in out
    assert "exceed threshold" in out


def test_log_next_action_recorded_on_log():
    import sqlite3

    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "d"]).stdout
    )
    log_out = runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "進捗",
            "--next-action",
            "テストを書く",
        ],
    )
    assert log_out.exit_code == 0
    log_id = _extract_id(log_out.stdout)
    db_path = os.environ["TK_DB_PATH"]
    conn = sqlite3.connect(db_path)
    row = conn.execute(
        "SELECT next_action_set FROM progress_logs WHERE id = ?", (log_id,)
    ).fetchone()
    conn.close()
    assert row[0] == "テストを書く"


def test_log_description_updates_task():
    task_id = _extract_id(
        runner.invoke(app, ["add", "T1", "--description", "initial-desc"]).stdout
    )
    runner.invoke(
        app,
        [
            "log",
            task_id,
            "--summary",
            "詳細を差し替え",
            "--description",
            "updated-desc",
        ],
    )
    show = runner.invoke(app, ["show", task_id]).stdout
    assert "updated-desc" in show
    assert "initial-desc" not in show
