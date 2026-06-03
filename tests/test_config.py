from pathlib import Path

import pytest

from tasukura.config import DEFAULT_DB_PATH, DEFAULT_DONE_RETENTION_DAYS, TkConfig


def test_default_config(tmp_path: Path):
    """存在しない設定ファイルの場合、デフォルト値が使われる."""
    config = TkConfig.load(config_path=tmp_path / "nonexistent.toml")
    assert config.db_path == DEFAULT_DB_PATH
    assert config.done_retention_days == DEFAULT_DONE_RETENTION_DAYS


def test_config_from_toml(tmp_path: Path):
    """config.tomlの値が正しく読み込まれる."""
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        'db_path = "/tmp/custom.db"\n\n[board]\ndone_retention_days = 7\n'
    )
    config = TkConfig.load(config_path=config_file)
    assert config.db_path == Path("/tmp/custom.db")
    assert config.done_retention_days == 7


def test_env_overrides_toml(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """環境変数TK_DB_PATHがtomlの値を上書きする."""
    config_file = tmp_path / "config.toml"
    config_file.write_text('db_path = "/tmp/from_toml.db"\n')
    monkeypatch.setenv("TK_DB_PATH", "/tmp/from_env.db")
    config = TkConfig.load(config_path=config_file)
    assert config.db_path == Path("/tmp/from_env.db")


def test_env_overrides_default(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """環境変数TK_DB_PATHがデフォルト値を上書きする."""
    monkeypatch.setenv("TK_DB_PATH", "/tmp/from_env.db")
    config = TkConfig.load(config_path=tmp_path / "nonexistent.toml")
    assert config.db_path == Path("/tmp/from_env.db")


def test_partial_toml(tmp_path: Path):
    """boardセクションのみのtomlでもdb_pathはデフォルトのまま."""
    config_file = tmp_path / "config.toml"
    config_file.write_text("[board]\ndone_retention_days = 3\n")
    config = TkConfig.load(config_path=config_file)
    assert config.db_path == DEFAULT_DB_PATH
    assert config.done_retention_days == 3


def test_config_record_defaults(tmp_path: Path):
    """recordセクションがないときはデフォルト値が使われる."""
    config = TkConfig.load(config_path=tmp_path / "nonexistent.toml")
    assert config.stale_after_days == 30
    assert config.active_warn_thresholds == {
        "decision": 10,
        "blocker": 3,
        "finding": 10,
        "question": 10,
        "hypothesis": 10,
    }


def test_config_record_overrides(tmp_path: Path):
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        "[record]\n"
        "stale_after_days = 7\n"
        "\n"
        "[record.active_warn]\n"
        "decision = 5\n"
        "blocker = 2\n"
    )
    config = TkConfig.load(config_path=config_file)
    assert config.stale_after_days == 7
    assert config.active_warn_thresholds["decision"] == 5
    assert config.active_warn_thresholds["blocker"] == 2
    assert config.active_warn_thresholds["finding"] == 10


def test_env_overrides_config_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """TK_CONFIG_PATH 環境変数で明示パス指定."""
    env_file = tmp_path / "env-config.toml"
    env_file.write_text("[record]\nstale_after_days = 99\n")
    monkeypatch.setenv("TK_CONFIG_PATH", str(env_file))
    config = TkConfig.load()
    assert config.stale_after_days == 99
