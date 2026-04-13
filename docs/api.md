# API 与 CLI

## FastAPI

### `GET /health`

- 返回数据库状态、LLM 状态和当前时间。

### `POST /runs/ingest`

- 请求体：
  - `sources`: 可选，来源列表
  - `from_at`: 可选，ISO 时间
  - `to_at`: 可选，ISO 时间
- 返回：
  - `run_id`
  - `status`
  - `sources`
  - `stored_items`

### `POST /runs/digest`

- 请求体：
  - `biz_date`: `YYYY-MM-DD`
- 返回：
  - `run_id`
  - `biz_date`
  - `cluster_count`
  - `llm_used`

### `GET /items`

- 查询参数：
  - `biz_date`
  - `source`
  - `topic`
  - `dedup_status`
  - `canonical_only`
- 返回规范化资讯项列表。

### `GET /digests/{biz_date}`

- 返回某日的最终日报，包括聚类条目、摘要、来源平台和重要性分数。

### `GET /sources`

- 返回当前配置文件中启用的来源与抓取规则。

## Typer CLI

### `aig config-check`

- 校验配置文件结构和启用来源。

### `aig ingest`

- 常用参数：
  - `--source`
  - `--from`
  - `--to`
- 示例：

```bash
uv run aig ingest --source github --source reddit
```

### `aig digest`

- 常用参数：
  - `--date YYYY-MM-DD`

### `aig backfill`

- 常用参数：
  - `--source`
  - `--days`
- 会按日期窗口回填，并在每天抓取后生成 digest。
