# 開発ワークフロー

[CONTRIBUTING.md](./CONTRIBUTING.md) に従うこと。特に以下を厳守：

- mainブランチに直接コミットしない。必ずfeatureブランチを切って作業する
- push前にCI相当のチェックを実行し、すべてパスすることを確認する：
  - `uv run pytest -v`
  - `uv run ruff check src/ tests/`
  - `uv run ruff format --check src/ tests/`
  - `uv run ty check src/`
