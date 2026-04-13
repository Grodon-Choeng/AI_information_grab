# 数据模型

## ingest_runs

- `id`: UUID 字符串主键
- `run_type`: `ingest` 或 `digest`
- `source`: 任务来源，批量任务可为空
- `status`: `running` / `succeeded` / `failed`
- `window_start_utc`
- `window_end_utc`
- `biz_date`
- `stats_json`
- `error_json`
- `started_at_utc`
- `finished_at_utc`

## source_checkpoints

- `source`: 主键
- `cursor_kind`: `published_at` 等
- `cursor_value`: ISO 时间字符串或来源游标
- `updated_at_utc`

## raw_items

- `id`: UUID 字符串主键
- `source`
- `source_item_id`
- `fetched_at_utc`
- `payload_json`
- 唯一约束：`(source, source_item_id)`

## normalized_items

- `id`: UUID 字符串主键
- `raw_item_id`
- `source`
- `source_item_id`
- `title`
- `author`
- `url`
- `normalized_url`
- `url_hash`
- `title_hash`
- `content_text`
- `published_at_utc`
- `biz_date`
- `source_score`
- `topic_hint`
- `cluster_id`
- `dedup_status`
- 唯一约束：`(source, source_item_id)`

## canonical_clusters

- `id`: UUID 字符串主键
- `biz_date`
- `dedup_key`
- `representative_title`
- `representative_url`
- `summary`
- `topic`
- `importance_score`
- `llm_used`
- `created_at_utc`

## cluster_members

- `id`: UUID 字符串主键
- `cluster_id`
- `item_id`
- `is_representative`
- 唯一约束：`(cluster_id, item_id)`

## daily_digests

- `id`: UUID 字符串主键
- `biz_date`
- `generated_at_utc`
- `cluster_count`
- `summary_markdown`
- `payload_json`
- 唯一约束：`biz_date`

## 去重策略与索引建议

- `raw_items(source, source_item_id)` 唯一约束保证硬去重。
- `normalized_items(url_hash, biz_date)` 支撑跨来源 URL 聚合。
- `normalized_items(title_hash, biz_date)` 支撑标题精确重复判断。
- `canonical_clusters(biz_date)` 支撑日报查询。
