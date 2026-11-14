# Contributing to tasukura

Thanks for your interest in contributing! This guide covers the basics for getting started.

## Development Setup

```bash
git clone https://github.com/mixidota2/tasukura
cd tasukura
uv sync
```

## Running Tests

```bash
uv run pytest -v
```

CI also builds a wheel from the exact checked-out commit and installs it with
currently resolved runtime dependencies in a separate environment for Python
3.11, 3.12, and 3.13. It runs the same tests and rejects source-checkout imports,
editable installs, package/version mismatches, and skipped tests. The existing
locked-dependency jobs remain separate. Dependency versions are printed in the
job log; a pass covers that resolution, not all future dependency versions.

To reproduce the wheel check locally (Linux/macOS):

```bash
wheel_dir=$(mktemp -d)
uv build --wheel --python 3.12 --out-dir "$wheel_dir/dist"
uv venv --python 3.12 "$wheel_dir/venv"
uv pip install --python "$wheel_dir/venv/bin/python" "$wheel_dir"/dist/*.whl 'pytest>=9.0.2'
PYTHONPATH= "$wheel_dir/venv/bin/python" scripts/check_installed_wheel.py
```

Do not run `uv sync` in that environment: it would replace the wheel with an
editable checkout. The check uses an isolated temporary HOME, clears inherited
`TK_DB_PATH`, `TK_CONFIG_PATH`, `PYTEST_ADDOPTS`, and `PYTEST_PLUGINS`, and disables
automatic plugin loading. It uses synthetic test databases, does not change the
release, and does not publish to a package registry.

## Code Quality

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [ty](https://github.com/astral-sh/ty) for type checking.

```bash
# Lint
uv run ruff check src/ tests/ scripts/

# Format
uv run ruff format src/ tests/ scripts/

# Type check
uv run ty check src/ scripts/
```

All three checks run in CI and must pass before merging.

## Submitting Changes

1. Fork the repository
2. Create a feature branch from `main`
3. Make your changes
4. Ensure all checks pass (`pytest`, `ruff check`, `ruff format --check`, `ty check`)
5. Open a pull request against `main`

Keep PRs focused — one feature or fix per PR.

## Reporting Issues

Use [GitHub Issues](https://github.com/mixidota2/tasukura/issues). Include:

- Steps to reproduce
- Expected vs. actual behavior
- Python version and OS
