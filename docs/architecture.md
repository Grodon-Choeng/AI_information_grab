# 架构说明

## 组件

- `FastAPI API`
  - 提供健康检查、手动抓取、手动日报生成、资讯查询和来源配置查看。
- `Typer CLI`
  - 提供本地开发和运维命令，包括抓取、回填和配置校验。
- `Worker`
  - 执行真正的抓取、规范化、去重、摘要、评分和日报生成。
- `Connectors`
  - 每个来源一个连接器，负责请求远端接口并输出统一的 `FetchedItem`。
- `PostgreSQL`
  - 保存原始抓取结果、规范化资讯、聚类结果、日报和来源检查点。
- `LLM Adapter`
  - 通过 Ollama 兼容接口调用本地模型，负责摘要、标签和评分。

## 数据流

1. CLI 或 API 触发一次 `ingest` 任务。
2. Worker 为本次任务分配 `run_id`，逐来源调用连接器。
3. 连接器拉取原始数据并转为统一 `FetchedItem`。
4. 系统先将原始载荷写入 `raw_items`，再写入 `normalized_items`。
5. 任务完成后更新 `source_checkpoints` 与 `ingest_runs`。
6. CLI 或 API 触发一次 `digest` 任务。
7. Worker 读取某个 `biz_date` 的 `normalized_items`，完成 URL 去重与标题近似聚类。
8. 对每个聚类生成摘要、主题和重要性评分，并写入 `canonical_clusters`、`cluster_members`、`daily_digests`。

## 时间策略

- 所有远端时间戳统一转换为 UTC 保存。
- 额外保存按 `Asia/Shanghai` 计算的 `biz_date`。
- 查询和日报以 `biz_date` 为主，而不是抓取执行时间。

## 失败恢复

- 单一来源失败不会影响其他来源继续抓取。
- LLM 调用失败不会阻断 digest，只会触发规则化降级。
- 重新执行相同日期的 `digest` 会覆盖该日期已有的聚类和日报，保证幂等。
- 重新执行相同窗口的 `ingest` 会依赖唯一约束和检查点避免重复数据。

## 日志约定

- 每次任务必须带 `run_id`。
- 每个来源至少记录以下步骤：
  - `start`
  - `fetch_done`
  - `normalize_done`
  - `dedup_done`
  - `digest_done`
  - `end`
- 关键字段：
  - `run_id`
  - `source`
  - `step`
  - `item_count`
  - `duration_ms`
  - `error_code`
  - `retryable`

## 调度策略

- v1 以 Typer CLI 和 FastAPI 手动触发为主。
- 后续可由系统 cron、容器调度器或任务平台定时调用 CLI/API。
- Worker 和数据库检查点设计为幂等，适合后续接入定时执行。
