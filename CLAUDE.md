# Development Workflow

Follow [CONTRIBUTING.md](./CONTRIBUTING.md). In particular:

- Never commit directly to main. Always create a feature branch first.
- Run all CI checks before pushing and ensure they pass:
  - `uv run pytest -v`
  - `uv run ruff check src/ tests/`
  - `uv run ruff format --check src/ tests/`
  - `uv run ty check src/`
