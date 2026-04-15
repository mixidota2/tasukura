# Changelog

## [0.1.1](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.0...tasukura-v0.1.1) (2026-04-15)


### Features

* **tk:** description(必須)・parent_id・next_action・updateコマンドを追加 ([d9e8697](https://github.com/mixidota2/tasukura/commit/d9e869707e7e4049d9932a3700e02fedbc639bdf))
* **tk:** rank, board, config, done retention を追加 ([e97abc0](https://github.com/mixidota2/tasukura/commit/e97abc045f45330f8e4dd033de77b0989981d1d4))


### Bug Fixes

* address security review findings (status validation, file permissions, connection leak) ([#2](https://github.com/mixidota2/tasukura/issues/2)) ([b604965](https://github.com/mixidota2/tasukura/commit/b604965c78bbd6663a85276c0da36176b2a78c10))


### Documentation

* add CONTRIBUTING.md and README badges for OSS readiness ([#1](https://github.com/mixidota2/tasukura/issues/1)) ([7dced80](https://github.com/mixidota2/tasukura/commit/7dced806b4505b6d6c6397ee40d94799fb54e08d))

## 0.1.0 (2026-04-14)

Initial release.

- Task CRUD with status management (todo/in_progress/in_review/done)
- Progress logging with summary, details, and remaining work
- Kanban board terminal display
- Hierarchical tasks (parent/child)
- Custom display ordering (rank)
- External source linking (source_id + source)
- TOML + environment variable configuration
