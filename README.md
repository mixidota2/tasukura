# tasukura

ローカル SQLite ベースのタスク管理 CLI。タスクと進捗をローカルに記録し、JIRA 連携レポートを生成する。

## インストール

```bash
# uv (推奨)
uv tool install tasukura

# pip
pip install tasukura

# GitHub から直接
uv tool install git+https://github.com/mixidota2/tasukura
```

CLI コマンドは `tk` として登録される。

## 使い方

```bash
# タスク追加
tk add "API実装" --description "REST APIのエンドポイントを実装する"

# 一覧表示
tk list

# ステータス変更
tk status <id> in_progress

# 進捗記録
tk log <id> --summary "エンドポイント実装完了" --details "GET /api/tasks を追加"

# カンバンボード表示
tk board

# 日次レポート
tk daily

# JIRA連携レポート
tk jira-report
```

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `tk add` | タスク追加 |
| `tk list` | タスク一覧（ツリー表示） |
| `tk update` | タスクのフィールド更新 |
| `tk status` | ステータス変更 (todo/in_progress/in_review/done) |
| `tk log` | 進捗ログ記録 |
| `tk rank` | 表示順序の変更 |
| `tk board` | カンバンボード表示 |
| `tk show` | タスク詳細表示 |
| `tk daily` | 日次進捗まとめ |
| `tk jira-report` | JIRA 向けレポート |

ID は先頭数文字の入力で一意に特定できれば省略可能。

## 設定

設定ファイル: `~/.config/tk/config.toml`

```toml
# データベースの保存先（デフォルト: ~/.local/share/tk/tasks.db）
db_path = "~/custom/path/tasks.db"

[board]
# 完了タスクの表示期間（デフォルト: 14日）
done_retention_days = 14
```

環境変数 `TK_DB_PATH` でデータベースパスを上書きできる。

## Claude Code スキル

`skill/` ディレクトリに Claude Code 用のスキルファイルが含まれている。

```bash
# スキルをインストール（シンボリックリンク推奨）
ln -s /path/to/tasukura/skill ~/.claude/skills/tk
```

詳細は [skill/skill.md](skill/skill.md) を参照。

## 開発

```bash
git clone https://github.com/mixidota2/tasukura
cd tasukura
uv sync
uv run pytest
```

## ライセンス

MIT
