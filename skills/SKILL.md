---
name: tk
description: >
  Local task management (tasukura). Add tasks, list, change status, and record progress.
  Use /task for task operations, /progress for progress logging.
  Also refer to this skill when proactively recording progress on commits or design decisions.
---

# tk - Local Task Management

Local SQLite-based task management CLI designed for AI coding agents. Track tasks and record progress.

## Execution (Strict)

**Always execute the `tk` command directly.**

```
# Correct (only this is allowed)
tk show <id>
tk list
tk add "Title" --description "..."

# Forbidden (never do this)
python -m tk ...
uv run tk ...
python tools/tk/main.py ...
```

`tk` is a CLI command registered in PATH. Execution via `python -m`, `uv run`, or `python` is strictly prohibited.

## Commands

| Command | Description |
|---------|-------------|
| `tk add "Title" --description "..." [--source-id ID] [--source TYPE] [--parent ID] [--next-action "..."] [--top] [--after ID]` | Add a task (description is required. --top for top position, --after to insert after a specific task) |
| `tk list [--status todo,in_progress] [--source TYPE] [--flat]` | List tasks (tree view by default) |
| `tk update <id> [--title "..."] [--description "..."] [--next-action "..."] [--source-id ID] [--source TYPE]` | Update task fields |
| `tk status <id> <new_status>` | Change status (todo/in_progress/in_review/done) |
| `tk log <id> --summary "..." [--details "..."] [--remaining "..."] [--next-action "..."]` | Record progress |
| `tk rank <id> [--after ID]` | Change display order (no args = move to top, --after = place after specified task) |
| `tk board [--status todo,in_progress]` | Kanban board view by status |
| `tk show <id>` | Show task details + logs + children |

IDs can be shortened — type just enough characters to uniquely identify a task.

## Task Fields

| Field | Description |
|-------|-------------|
| `title` | Task name (short) |
| `description` | Goal, acceptance criteria, and background (**required**) |
| `next_action` | Next step to take. Displayed as `->` in `tk list` |
| `status` | todo / in_progress / in_review / done |
| `position` | Display order (lower = higher priority. Change with `tk rank`) |
| `source_id` | External source identifier (e.g. PROJ-123, #456) |
| `source` | Source type (e.g. jira, github, linear) |
| `parent_id` | Parent task ID. Supports multiple levels |

## Operation Flows

### `/task` — Task Operations

Interpret user intent and execute the appropriate command:
- "Add a task" → `tk add` (confirm description with user)
- "List tasks" → `tk list`
- "Start working on X" → `tk status <id> in_progress`
- "X is ready for review" → `tk status <id> in_review`
- "Update next action" → `tk update <id> --next-action "..."`
- "Move X to the top" → `tk rank <id>`
- "Move after X" → `tk rank <id> --after <other_id>`

#### When to use in_review

Set status to `in_review` when:
- A PR has been submitted and is awaiting review
- Waiting for user confirmation or decision
- Waiting for a response from another team

`in_review` = no action needed from you; waiting on someone else.

#### Adding tasks from external sources

When adding with `--source-id` and `--source`, **always retrieve the source description first** and include it **verbatim** (no summarization) in the tk description. All information from the source (background, requirements, steps, links, etc.) must be preserved in the tk description.

Steps:
1. Retrieve the ticket/issue description from the external source
2. Include the content **as-is** (preserving structure, lists, links) in `--description`. Do not summarize
3. Set the first step as `--next-action`

### `/progress` — Progress Logging

Record progress based on user instruction or your own judgment:

1. `tk list --status in_progress` to find active tasks
2. `tk log` to record progress on the relevant task
3. `tk status` to change status if needed
4. Update `--next-action` if the next step has changed

## Proactive Progress Logging

Record progress without user instruction at these moments:
- On commit
- When a design decision or approach is finalized
- When investigation or analysis reaches a milestone
- When a blocker appears or is resolved

Steps:
1. `tk list --status todo,in_progress` to find the relevant task
2. `tk log <id>` to record
3. Skip if no relevant task exists (do not create tasks without user confirmation)

## Progress Log Guidelines

Logs should contain **enough context for another AI agent to pick up or resume the task**.

### Always include `--details`

A log with only `--summary` is insufficient. **`--details` is mandatory**.

- **`--summary`**: One-line description of what was done or what happened
- **`--details`** (required): Include:
  - Reasoning, investigation results, what was tried
  - Technical specifics (file names, line numbers, metrics)
  - Artifacts created (ticket numbers, PR numbers, branch names)
  - List of changed files
  - Enough detail for the next agent to understand "why this state" and "how far along"
- **`--remaining`**: Remaining work or blockers
- **`--next-action`**: Update the task's next action (updates the task record simultaneously)

### Bad vs. Good Examples

**Bad (insufficient):**
```
tk log <id> --summary "Created 7 tickets in JIRA"
```

**Good (detailed):**
```
tk log <id> --summary "Completed investigation and ticketing for auth module refactor" \
  --details "Investigated the full repository and created 3 tickets:
1. PROJ-101: Extract shared validation logic - utils.py overlap ~90%
2. PROJ-102: Unify error handling - identified inconsistent response format
..."
```

Logs may be forwarded to external systems, so write them clearly enough for third parties to understand.
