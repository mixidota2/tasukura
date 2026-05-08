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
| `tk update` | Update task fields |
| `tk delete` | Delete a task and its progress logs |
| `tk status` | Change task status (todo/in_progress/in_review/done) |
| `tk log` | Record a progress log entry |
| `tk log-update` | Update an existing progress log entry |
| `tk log-delete` | Delete a progress log entry |
| `tk rank` | Change display order |
| `tk board` | Kanban board view |
| `tk show` | Show task details and progress logs |

Task IDs can be shortened — type just enough characters to uniquely identify a task.

## Configuration

Config file: `~/.config/tk/config.toml`

```toml
# Database path (default: ~/.local/share/tk/tasks.db)
db_path = "~/custom/path/tasks.db"

[board]
# Retention days for done tasks (default: 14)
done_retention_days = 14
```

The environment variable `TK_DB_PATH` overrides the database path.

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
