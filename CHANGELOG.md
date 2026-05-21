# Changelog

## [0.1.6](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.5...tasukura-v0.1.6) (2026-05-08)


### Documentation

* Add log-update and log-delete to README commands table ([#17](https://github.com/mixidota2/tasukura/issues/17)) ([b5c8a11](https://github.com/mixidota2/tasukura/commit/b5c8a11a6ee9037405ba6d24a95a62077512ac73))

## [0.1.5](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.4...tasukura-v0.1.5) (2026-05-07)


### Features

* add log-update and log-delete commands ([#14](https://github.com/mixidota2/tasukura/issues/14)) ([4bab3b8](https://github.com/mixidota2/tasukura/commit/4bab3b8757b2d43978fc9fbffbfee1424cc75d80))

## [0.1.4](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.3...tasukura-v0.1.4) (2026-04-16)


### Bug Fixes

* use PAT for release-please to trigger publish workflow ([#12](https://github.com/mixidota2/tasukura/issues/12)) ([94d64d6](https://github.com/mixidota2/tasukura/commit/94d64d63f92353d8037aea9333630299449fb174))

## [0.1.3](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.2...tasukura-v0.1.3) (2026-04-16)


### Documentation

* Replace hardcoded examples with generic placeholders in skill doc ([#10](https://github.com/mixidota2/tasukura/issues/10)) ([d14b8c4](https://github.com/mixidota2/tasukura/commit/d14b8c4100792e98608c0fe8e6cb516c9694b14f))

## [0.1.2](https://github.com/mixidota2/tasukura/compare/tasukura-v0.1.1...tasukura-v0.1.2) (2026-04-16)


### Features

* Add tk delete command ([#6](https://github.com/mixidota2/tasukura/issues/6)) ([194e1ec](https://github.com/mixidota2/tasukura/commit/194e1ecd8f5427b6d4de45a77530c9064b44deec))


### Bug Fixes

* optimize DB queries for partial ID resolution and child task fetch ([#5](https://github.com/mixidota2/tasukura/issues/5)) ([58edc6f](https://github.com/mixidota2/tasukura/commit/58edc6f09da9481ffa279d7a810f75798e9a176e))

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
