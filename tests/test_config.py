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
