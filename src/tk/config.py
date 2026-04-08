"""tk の設定管理.

設定ファイル: ~/.config/tk/config.toml
優先順位: 環境変数 > config.toml > デフォルト値
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

try:
    import tomllib
except ImportError:
    import tomli as tomllib  # type: ignore[no-redefine]

DEFAULT_CONFIG_PATH = Path.home() / ".config" / "tk" / "config.toml"
DEFAULT_DB_PATH = Path.home() / ".local" / "share" / "tk" / "tasks.db"
DEFAULT_DONE_RETENTION_DAYS = 14


@dataclass(frozen=True)
class TkConfig:
    """tkの設定."""

    db_path: Path = field(default=DEFAULT_DB_PATH)
    done_retention_days: int = field(default=DEFAULT_DONE_RETENTION_DAYS)

    @classmethod
    def load(cls, config_path: Path | None = None) -> "TkConfig":
        """設定を読み込む。環境変数 > config.toml > デフォルト."""
        db_path = DEFAULT_DB_PATH
        done_retention_days = DEFAULT_DONE_RETENTION_DAYS

        # config.toml から読み込み
        path = config_path or DEFAULT_CONFIG_PATH
        if path.exists():
            with open(path, "rb") as f:
                data = tomllib.load(f)
            if "db_path" in data:
                db_path = Path(data["db_path"]).expanduser()
            board = data.get("board", {})
            if "done_retention_days" in board:
                done_retention_days = int(board["done_retention_days"])

        # 環境変数で上書き
        env_db = os.environ.get("TK_DB_PATH")
        if env_db:
            db_path = Path(env_db)

        return cls(db_path=db_path, done_retention_days=done_retention_days)
