"""tk の設定管理.

設定ファイル: ~/.config/tk/config.toml
優先順位: 環境変数 > config.toml > デフォルト値
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

import tomllib

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tk" / "config.toml"
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tk" / "tasks.db"
DEFAULT_DONE_RETENTION_DAYS = 14
DEFAULT_STALE_AFTER_DAYS = 30
DEFAULT_ACTIVE_WARN = {
    "decision": 10,
    "blocker": 3,
    "finding": 10,
    "question": 10,
    "hypothesis": 10,
}


@dataclass(frozen=True)
class TkConfig:
    """tkの設定."""

    db_path: Path = field(default=DEFAULT_DB_PATH)
    done_retention_days: int = field(default=DEFAULT_DONE_RETENTION_DAYS)
    stale_after_days: int = field(default=DEFAULT_STALE_AFTER_DAYS)
    active_warn_thresholds: dict[str, int] = field(
        default_factory=lambda: dict(DEFAULT_ACTIVE_WARN)
    )

    @classmethod
    def load(cls, config_path: Path | None = None) -> "TkConfig":
        """設定を読み込む。環境変数 > config.toml > デフォルト."""
        db_path = DEFAULT_DB_PATH
        done_retention_days = DEFAULT_DONE_RETENTION_DAYS
        stale_after_days = DEFAULT_STALE_AFTER_DAYS
        active_warn = dict(DEFAULT_ACTIVE_WARN)

        # Honor explicit config path override
        env_cfg = os.environ.get("TK_CONFIG_PATH")
        if env_cfg:
            path = Path(env_cfg)
        else:
            path = config_path or DEFAULT_CONFIG_PATH

        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)
            if "db_path" in data:
                db_path = Path(data["db_path"]).expanduser()
            board = data.get("board", {})
            if "done_retention_days" in board:
                done_retention_days = int(board["done_retention_days"])
            record = data.get("record", {})
            if "stale_after_days" in record:
                stale_after_days = int(record["stale_after_days"])
            for kind, threshold in record.get("active_warn", {}).items():
                active_warn[kind] = int(threshold)

        env_db = os.environ.get("TK_DB_PATH")
        if env_db:
            db_path = Path(env_db)

        return cls(
            db_path=db_path,
            done_retention_days=done_retention_days,
            stale_after_days=stale_after_days,
            active_warn_thresholds=active_warn,
        )
