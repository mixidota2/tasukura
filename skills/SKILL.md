---
name: tk
description: >
  Local task management (tasukura). Two-layer memory model: progress_logs (raw timeseries)
  and typed records (extracted knowledge). Use /task for task ops, /progress for logging.
  Refer to this skill before recording progress, decisions, findings, or blockers.
---

# tk - Local Task Management

Local SQLite-based task management CLI designed for AI coding agents. Two-layer memory
model: progress_logs (raw timeseries) + typed records (extracted knowledge).

## Execution (Strict)

Always execute the `tk` command directly. `tk` is registered in PATH; do NOT use
`uv run tk`, `python -m tasukura`, etc.

## Commands

| Command | Description |
|---------|-------------|
| `tk add "Title" --description "..." [--source-id ID] [--source TYPE] [--parent ID] [--next-action "..."] [--top] [--after ID]` | Add a task (description required) |
| `tk list [--status todo,in_progress] [--source TYPE] [--flat]` | List tasks (tree by default) |
| `tk update <id> [--title "..."] [--source-id ID] [--source TYPE]` | Update title or external source linkage. For next_action / description, use `tk log` |
| `tk delete <id>` | Delete task (fails cleanly if records exist) |
| `tk status <id> <new_status>` | Change status (todo/in_progress/in_review/done) |
| `tk log <id> --summary "..." [--details "..."] [--remaining "..."] [--next-action "..."] [--description "..."]` | Record progress. `--next-action` updates task and is persisted as `next_action_set` on the log (history). `--description` updates task only |
| `tk log-update <log_id> [--summary "..."] [--details "..."] [--remaining "..."]` | Edit a log (empty string clears) |
| `tk log-delete <log_id>` | Delete a log (fails cleanly if a record references it) |
| `tk record add <task_id> --kind <decision\|finding\|blocker\|question\|hypothesis> --log-id <log_id> --summary "..." [--details "..."] [--supersedes <record_id>]` | Add a typed record extracted from a log |
| `tk record list <task_id> [--kind X] [--all]` | List records (active by default) |
| `tk record show <record_id> [--with-log]` | Show record; `--with-log` dereferences source log |
| `tk record update <record_id> [--summary "..."] [--details "..."]` | Typo / 補足 only |
| `tk record resolve <blocker_id>` | Mark blocker resolved |
| `tk record obsolete <id>` | Retire a record without replacement |
| `tk record verify <id>` | Update last_verified_at (re-confirmed valid) |
| `tk rank <id> [--after ID]` | Reorder |
| `tk board [--status ...]` | Kanban view |
| `tk show <id> [--full] [--kind X] [--logs N]` | Active context view |

IDs accept prefix matches (12-char short IDs displayed).

## Two-Layer Memory Model

```
progress_logs   <- 時系列の raw trace (経緯・調査過程・議論・代替案)
   │
   │ 抽出・要約 (--log-id で明示昇格)
   ▼
records         <- typed memory (結論・根拠・スコープのみ)
   │
   │ 自動絞り込み (status/freshness/threshold)
   ▼
tk show         <- active context (LLM が毎ターン読む対象)
```

**Cardinality rule of thumb:** Most logs do **not** become records. Records are for facts
an agent should re-read in future sessions.

## When to use what

### tk log (常に書く)

- Commit のたび
- 進捗の節目
- 設計議論を「経緯」として言語化する瞬間
- ブロッカーの発生・解消
- 失敗した試行 (`attempt`) — record には上げない
- 詳しい経緯は `--details` へ。これが後で record の raw evidence になる

### tk record add (昇格判断したときだけ)

| kind | 適用 |
|------|------|
| `decision` | 設計・方針・制約が確定したとき |
| `finding` | 調査・検証で**事実**が判明したとき |
| `blocker` | 障害として将来再参照される見込みがあるとき |
| `question` | 未確定だが**明示的に**追跡したい論点 |
| `hypothesis` | 「Xだろう」と仮置きで動いている、未検証 |

**手順:**

1. `tk record list <task_id> --kind <X>` で既存 active を確認 (dedup責任)
2. 重複なら supersede: `tk record add ... --supersedes <old_id>` (旧は自動 superseded)
3. 重複なしならそのまま `tk record add ... --log-id <log_id>`

`--log-id` は **必須**。昇格制 (raw → typed) を強制し、root cause 不明の record を防ぐ。

### record の内容ガイドライン (抽出・要約)

研究文書 (Memori の semantic triples、From Storage to Experience の trajectory abstraction)
のプラクティス。record は raw のコピーではなく、**結論を抽出した typed memory**。

| フィールド | 書く | 書かない |
|------------|------|---------|
| `record.summary` | 結論を1行 (「採用した」「判明した」「起きた」) | 経緯、代替案 |
| `record.details` | 結論の本質的根拠 / スコープ / 制約 / 再検討トリガー | 経緯、調査過程、却下した代替案 |
| `log.summary` | その瞬間の活動を1行 | — |
| `log.details` | 経緯・調査過程・議論・代替案 (raw evidence) | — |

**Bad (log を record にコピー):**

```
log.details   = "OIDC/Auth0/自前を比較。OIDC: 標準準拠、メンテコスト中。Auth0: SaaS、コスト高。自前: 学習コスト高。結論: OIDC"
record.details = "OIDC/Auth0/自前を比較。OIDC: 標準準拠..."   ← log の丸ごとコピー
```

**Good (結論を抽出):**

```
log.details   = "<上と同じ経緯>"
record.summary = "認証にOIDCを採用"
record.details = "判断軸: メンテコストと標準化のバランス、ロックイン回避
                  スコープ: 認証関連の全モジュール
                  再検討トリガー: SaaS切替を検討する場合"
```

経緯を後で見たいときは `tk record show R-xxx --with-log` で source log を dereference。

## Lifecycle

```
add (--supersedes <old>)
  └─ 旧 record の status を superseded に自動 flip
update (typo / 補足のみ)
  └─ 意味が変わるなら必ず add --supersedes を使う
resolve (blocker のみ)
  └─ status=resolved, resolved_at=now
obsolete (置換 record なしで現役から外す)
  └─ status=obsolete
verify (内容変更なし)
  └─ last_verified_at=now (stale警告の解除)
```

## tk show の読み方

デフォルト出力:

```
Active Decisions (N):
  R-xxxx  <summary> [stale]?
  ...

Active Blockers (N):  ...
Open Findings (N):    ...
Open Questions (N):   ...
Open Hypotheses (N):  ...

Recent logs (5):
  L-xxxx  [date] <summary>

⚠ Active <kind>s (N) exceed threshold (K) — consider obsolete/supersede
```

- **ID + summary だけ**を読み、詳細は必要時に `tk record show R-xxx` で dereference。
- `[stale]` マーク = `last_verified_at` (なければ `created_at`) が `stale_after_days` 超
   → `tk record verify` か `tk record obsolete` を選ぶ
- 警告 = active set 肥大化のサイン → obsolete / supersede で整理

オプション: `--full` (inactive と全 log), `--kind <X>` (絞り込み), `--logs N` (件数変更)

## Operation Flows

### `/task` — Task operations

User intent → command mapping:

- "Add a task" → `tk add` (description を一緒に確認)
- "Start working on X" → `tk status <id> in_progress`
- "X is ready for review" → `tk status <id> in_review`
- "Update next action" → `tk log <id> --summary "..." --next-action "..."` (履歴も残る)
- "Update description" → `tk log <id> --summary "..." --description "..."`
- "Move X to the top" → `tk rank <id>`

#### When to use in_review

PR submitted / waiting on user / waiting on another team — i.e., no agent action needed.

#### Adding tasks from external sources

外部チケットからタスクを作るときは **必ず元情報を verbatim** で description に含める (要約しない)。
理由: research note の Storage 層は raw を保持する原則。

```
1. 外部 (JIRA, GitHub) から description を取得
2. 構造・リスト・リンクをそのまま --description に入れる
3. 最初の手を --next-action に入れる
```

### `/progress` — Progress logging

1. `tk list --status in_progress` で active task を見つける
2. `tk log <id> --summary "..." --details "..."`
3. 状態が変わるなら `tk status` / `tk log --next-action`

### Proactive logging

ユーザー指示なしで自動で書くタイミング:

| タイミング | log | record |
|------------|-----|--------|
| コミット時 | ✅ `tk log` | ❌ (区切り commit でなければ) |
| 設計判断が確定 | ✅ 経緯を `--details` に | ✅ `tk record add --kind decision --log-id <log>` |
| 調査が確定 (finding) | ✅ 経緯 | ✅ `--kind finding` |
| ブロッカー発生 | ✅ 発生状況 | ✅ (将来再参照されるなら) `--kind blocker` |
| ブロッカー解消 | ✅ 解消経緯 | ✅ `tk record resolve <blocker_id>` |
| 失敗した試行 | ✅ | ❌ (attempt は records に上げない) |

**判断順序**: log を書く → 「これは将来再参照する価値があるか?」 → Yes なら record に昇格。

### Stale 対応

`[stale]` マークを見たら:

1. `tk record show R-xxx` で内容確認 (必要なら `--with-log` で経緯も)
2. **今も有効** → `tk record verify R-xxx`
3. **古くなって無効** → `tk record obsolete R-xxx`
4. **新しい判断に置き換える** → `tk log` で経緯 → `tk record add --supersedes R-xxx ...`

連続 update で typed memory を壊さない (研究文書: "useful memories become faulty when
continuously updated") — 内容変更は必ず supersede で。

## Configuration

`~/.config/tk/config.toml`:

```toml
db_path = "~/.local/share/tk/tasks.db"

[board]
done_retention_days = 14

[record]
stale_after_days = 30          # default

[record.active_warn]
decision = 10                  # default
blocker = 3                    # default
finding = 10                   # default
question = 10                  # default
hypothesis = 10                # default
```

Environment overrides: `TK_DB_PATH` (db path), `TK_CONFIG_PATH` (config file).
