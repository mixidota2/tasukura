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

## Code Quality

This project uses [ruff](https://docs.astral.sh/ruff/) for linting and formatting, and [ty](https://github.com/astral-sh/ty) for type checking.

```bash
# Lint
uv run ruff check src/ tests/

# Format
uv run ruff format src/ tests/

# Type check
uv run ty check src/
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
