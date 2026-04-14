---
name: tk
description: >
  ローカルタスク管理（tasukura）。タスクの追加・一覧・状態変更・進捗記録を行う。
  /task でタスク操作、/progress で進捗記録、/daily-report で日次まとめ。
  また、実装完了やコミット時に自発的に進捗を記録する際にもこのスキルを参照する。
---

# tk - ローカルタスク管理

ローカルSQLiteベースのタスク管理CLI。進捗を記録し、JIRA反映用レポートを生成する。

## 実行方法（厳守）

**`tk` コマンドは必ずそのまま直接実行すること。**

```
# 正しい（これ以外は禁止）
tk show <id>
tk list
tk add "タイトル" --description "..."

# 禁止（絶対にやるな）
python -m tk ...
uv run tk ...
python tools/tk/main.py ...
```

`tk` はPATHに登録済みのCLIコマンドである。`python -m`、`uv run`、`python` 経由での実行は一切禁止。違反した場合ユーザー体験を損なう。

## コマンド一覧

| コマンド | 説明 |
|---------|------|
| `tk add "タイトル" --description "..." [--jira PROJ-123] [--parent ID] [--next-action "..."] [--top] [--after ID]` | タスク追加（descriptionは必須。--topで最上位、--afterで指定タスクの後ろに追加） |
| `tk list [--status todo,in_progress] [--jira-only] [--flat]` | タスク一覧（デフォルトツリー表示） |
| `tk update <id> [--title "..."] [--description "..."] [--next-action "..."] [--jira KEY]` | タスクのフィールド更新 |
| `tk status <id> <new_status>` | ステータス変更（todo/in_progress/in_review/done） |
| `tk log <id> --summary "..." [--details "..."] [--remaining "..."] [--next-action "..."]` | 進捗記録 |
| `tk rank <id> [--after ID]` | 表示順序を変更（引数なしで最上位、--afterで指定タスクの後ろ） |
| `tk board [--status todo,in_progress]` | カンバンボード風にステータス別表示 |
| `tk show <id>` | タスク詳細+ログ+子タスク表示 |
| `tk daily [--date YYYY-MM-DD]` | 日次進捗まとめ |
| `tk jira-report [--date YYYY-MM-DD]` | JIRA向けレポート |

IDは先頭数文字の入力で一意に特定できれば省略可能。

## タスクのフィールド

| フィールド | 説明 |
|-----------|------|
| `title` | タスク名（短い名前） |
| `description` | タスクのゴール・完了条件・背景（**必須**）。JIRAのdescriptionに対応 |
| `next_action` | 次にやるべきこと。`tk list` で `->` として表示される |
| `status` | todo / in_progress / in_review / done |
| `position` | 表示順序（小さいほど上位。`tk rank` で変更） |
| `jira_key` | JIRAチケットキー（例: PROJ-123） |
| `parent_id` | 親タスクID。多階層対応 |

## 操作フロー

### `/task` — タスク操作

ユーザーの意図を解釈して適切なコマンドを実行する:
- 「タスク追加して」→ `tk add`（descriptionをユーザーに確認する）
- 「タスク一覧」→ `tk list`
- 「〇〇を着手にして」→ `tk status <id> in_progress`
- 「〇〇をレビュー待ちにして」→ `tk status <id> in_review`
- 「次やることを更新して」→ `tk update <id> --next-action "..."`
- 「〇〇を一番上にして」→ `tk rank <id>`
- 「〇〇の後ろに移動」→ `tk rank <id> --after <other_id>`

#### in_review の使いどころ

以下のタイミングで `in_review` に変更する:
- PRを出してレビュー待ちのとき
- ユーザーに確認・判断を待っているとき
- 他チームへの依頼の返答待ちのとき

自分のアクションが不要で、他者の応答を待っている状態 = `in_review`。

#### JIRAチケットからのタスク追加

`--jira` 付きでタスクを追加する場合、**必ず先にJIRAチケットのdescriptionを取得**し、その内容を**要約せずそのまま**tkのdescriptionに反映する。JIRAのdescriptionに書かれている情報（背景・理由・手順・要件・リンク等）はすべてtkのdescriptionに含めること。要約・省略・言い換えは不可。JIRAのdescriptionがtkを見るだけで完全に再現できる状態にする。

手順:
1. `getJiraIssue` でチケットの description を取得（`responseContentFormat: "markdown"`）
2. description の内容を**そのまま**（構造・箇条書き・リンク含め）tk の `--description` に反映。要約しない
3. 最初の手順を `--next-action` に設定

### `/progress` — 進捗記録

ユーザーの指示、またはClaude自身の判断で進捗を記録する:

1. `tk list --status in_progress` で進行中タスクを確認
2. 該当タスクに `tk log` で記録
3. 必要に応じて `tk status` でステータス変更
4. 次のアクションが変わった場合は `--next-action` も更新

### `/daily-report` — 日次レポート

1. `tk daily` で今日の進捗を表示
2. `tk jira-report` でJIRA向けレポートを表示
3. JIRA連携タスクがあれば、各チケットについて以下をユーザーに提案する:
   - 進捗コメントの追加（jira-reportの内容をベースに）
   - ステータス変更が必要な場合はその旨も提案
   - ユーザーのOK後に `/jira` スキルで実行

## 自発的な進捗記録

以下のタイミングでは、ユーザーの指示がなくてもこのスキルに従い進捗を記録する:
- コミット時
- 設計・方針が決まったとき
- 調査・分析が一段落したとき
- ブロッカーが発生/解消したとき

手順:
1. `tk list --status todo,in_progress` で関連タスクを特定
2. 該当タスクに `tk log` で記録
3. 該当タスクがなければ記録をスキップ（新規タスク作成はユーザーに確認）

## 進捗ログの記録方針

ログは **別のAIエージェントがこのタスクを引き継いだり再開したりする際に、必要なコンテキストがすべて揃っている状態** を目指して記録する。

### 必須: `--details` を常に付与する

`--summary` だけのログは情報不足。**`--details` は省略不可**。summaryは1行の要約、detailsに具体的な内容を書く。

具体的には:
- **`--summary`**: 何をしたか／何が起きたかの1行要約
- **`--details`**（必須）: 以下を含めて記述する
  - 判断の背景、調査結果、試したこと
  - 技術的な詳細（具体的なファイル名、行数、数値データ等）
  - 作成したもの（チケット番号、PR番号、ブランチ名等）
  - 変更したファイルの一覧
  - 次にこのタスクに取り組むエージェントが「なぜこうなっているのか」「どこまで進んだのか」を理解できる粒度で書く
- **`--remaining`**: 残作業やブロッカー
- **`--next-action`**: タスクの次のアクションを更新（ログと同時にタスク本体のnext_actionが更新される）

### 悪い例と良い例

**悪い例（情報不足）:**
```
tk log <id> --summary "7件のチケットをJIRAに作成完了"
```

**良い例（詳細あり）:**
```
tk log <id> --summary "RS MLパイプラインのリファクタリング調査・チケット化完了" \
  --details "リポジトリ全体を調査し、以下7件のJIRAチケットを作成した。
1. RECOIH-1670: ials/add_free_ialsの統一化検討 - config.py重複度~100%, component.py重複度~80%
2. RECOIH-1671: パイプライン構造の統一検討 - query_params型不統一を特定
..."
```

ログは後からJIRAコメントに転記されるため、第三者が読んでも分かる記述を心がける。
