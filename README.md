# tasukura

[![CI](https://github.com/mixidota2/tasukura/actions/workflows/ci.yml/badge.svg)](https://github.com/mixidota2/tasukura/actions/workflows/ci.yml)
[![PyPI](https://img.shields.io/pypi/v/tasukura)](https://pypi.org/project/tasukura/)
[![Python](https://img.shields.io/pypi/pyversions/tasukura)](https://pypi.org/project/tasukura/)
[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

A local task management CLI designed for AI coding agents. Track tasks and progress in SQLite — lightweight, portable, and agent-friendly.

## Features

- **Task lifecycle** — status transitions: todo / in_progress / in_review / done
- **Progress logging** — structured fields: summary, details, remaining, next action
- **External source linking** — link tasks to JIRA, GitHub Issues, Linear, or any external system
- **SQLite storage** — single-file database, zero infrastructure

## Installation

```bash
# uv (recommended)
uv tool install tasukura

# pip
pip install tasukura

# From source
uv tool install git+https://github.com/mixidota2/tasukura
```

The CLI is registered as `tk`.

## Quick Start

```bash
# Add a task
tk add "Implement API" --description "Build REST API endpoints for /tasks"

# List tasks
tk list

# Change status
tk status <id> in_progress

# Log progress
tk log <id> --summary "Endpoints done" --details "Added GET/POST /api/tasks"

# Link to an external source
tk add "Fix login bug" --description "..." --source-id PROJ-123 --source jira

# Filter by source
tk list --source jira
```

## Commands

| Command | Description |
|---------|-------------|
| `tk add` | Add a new task |
| `tk list` | List tasks (tree view by default) |
| `tk update` | Update task title or external source linkage. For `next_action` or `description` use `tk log` |
| `tk delete` | Delete a task (fails cleanly if records exist) |
| `tk status` | Change task status (todo/in_progress/in_review/done) |
| `tk log` | Record progress. `--next-action "X"` updates task and persists as log history; `--description "X"` updates task description |
| `tk log-update` | Update an existing progress log entry |
| `tk log-delete` | Delete a progress log (fails cleanly if a record references it) |
| `tk record add` | Add a typed record (decision/finding/blocker/question/hypothesis) promoted from a log; `--supersedes <id>` to replace an older record |
| `tk record list` | List records for a task (active by default) |
| `tk record show` | Show a record's full details; `--with-log` also dereferences the source progress log |
| `tk record update` | Update a record's summary or details (typo / 補足 only; use `--supersedes` on add for semantic changes) |
| `tk record resolve` | Mark a blocker record as resolved |
| `tk record obsolete` | Mark a record as obsolete (no replacement) |
| `tk record verify` | Mark a record as verified (update last_verified_at) |
| `tk record delete` | Permanently delete a mistaken record (prefer `obsolete` for valid records) |
| `tk rank` | Change display order |
| `tk board` | Kanban board view |
| `tk show` | Show task details, active records grouped by kind, and recent logs. `--full` / `--kind X` / `--logs N` to vary |

Task IDs can be shortened — type just enough characters to uniquely identify a task.

## Configuration

Config file: `~/.config/tk/config.toml`

```toml
# Database path (default: ~/.local/share/tk/tasks.db)
db_path = "~/custom/path/tasks.db"

[board]
# Retention days for done tasks (default: 14)
done_retention_days = 14

[record]
# Mark active records older than this (no verify) as [stale] in `tk show`
stale_after_days = 30

[record.active_warn]
# `tk show` warns when active records of a kind exceed these counts
decision = 10
blocker = 3
finding = 10
question = 10
hypothesis = 10
```

The environment variable `TK_DB_PATH` overrides the database path. `TK_CONFIG_PATH` overrides the config file location.

## Claude Code Skill

The `skills/` directory contains a [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill file for AI agent integration.

```bash
# Install the skill (symlink recommended)
ln -s /path/to/tasukura/skills ~/.claude/skills/tk
```

See [skills/SKILL.md](skills/SKILL.md) for details.

## Development

```bash
git clone https://github.com/mixidota2/tasukura
cd tasukura
uv sync
uv run pytest
```

## License

MIT
