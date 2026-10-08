# tasukura skill setup

The `tk` agent skill now lives in
[tasukura-skills](https://github.com/mixidota2/tasukura-skills).
This directory contains only this guide; it no longer provides an installable
`SKILL.md`.

## New installations

Follow the separate repository's
[installation guide](https://github.com/mixidota2/tasukura-skills#install).
It covers installing the `tasukura` CLI, cloning the skill repository, and setting
up the skill for Claude Code or Codex.

Install the skill from `tasukura-skills/skills/tk`, not from this directory.
The CLI continues to be maintained and distributed from the main
[tasukura repository](https://github.com/mixidota2/tasukura).

## Existing installations

If `~/.claude/skills/tk` or `~/.agents/skills/tk` links to this repository's
`skills/` directory, **updating this checkout removes the `SKILL.md` the agent
needs**. The directory and symlink may still exist, but the old location will no
longer provide the `tk` skill. Migrate before updating when possible, or follow
the same guide afterward if you have already updated.

Use the separate repository's
[migration guide](https://github.com/mixidota2/tasukura-skills#migrate-an-existing-installation)
to back up the old installation and point your agent at the new checkout. The
guide preserves local customizations and handles existing or broken symlinks.
A copied installation remains available until you replace it, but it will not
receive updates from the new repository automatically.

This change does not move or modify the `tk` CLI, task database, or CLI
configuration. Future skill changes belong in `tasukura-skills`.
