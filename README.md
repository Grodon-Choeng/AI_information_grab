# AI Information Grab

`AI Information Grab` 是一个面向个人或小团队的 AI 资讯抓取与汇总服务。它会从 GitHub、Reddit、Hacker News 等来源抓取 AI 相关信息，在本地完成落库、去重、摘要、评分和日报生成，并通过 FastAPI 与 Typer 提供查询和运维入口。

## 目标

- 支持多来源、可配置的 AI 资讯抓取。
- 使用本地 PostgreSQL 保存原始数据、规范化数据、聚类结果和日报。
- 对跨平台重复事件做统一归并。
- 默认启用本地 LLM 做摘要、标签和评分，但在模型不可用时能够自动降级。
- 通过 FastAPI API、Typer CLI 和独立 Worker 完成开发与运行闭环。

## v1 范围

- 来源：GitHub、Reddit、Hacker News。
- 抓取方式：HTTP API / JSON 接口，统一使用 `httpx`。
- 持久化：Docker 中的 PostgreSQL。
- 展示：FastAPI 查询接口、Typer 命令和 Markdown 日报数据。
- 非目标：前端页面、消息推送、登录态抓取、Twitter/X 正式接入。

## 快速开始

1. 创建环境变量文件：

```bash
cp .env.example .env
```

2. 启动 PostgreSQL：

```bash
docker compose up -d postgres
```

3. 安装依赖：

```bash
uv sync --extra dev
```

4. 初始化数据库结构：

```bash
uv run alembic upgrade head
```

5. 校验配置并运行一次抓取：

```bash
uv run aig config-check
uv run aig ingest --source github --source reddit --source hackernews
uv run aig digest --date 2026-04-13
```

6. 启动 API：

```bash
uv run uvicorn app.main:app --reload
```

## 运行方式

- API：FastAPI 提供健康检查、手动触发抓取、手动触发汇总、资讯查询和来源配置查看。
- CLI：Typer 提供本地开发、自定义时间窗口抓取、回填和配置校验。
- Worker：由 CLI 或 API 触发任务执行，负责抓取、落库、去重、摘要和日报生成。

## 本地 LLM

- 默认按 Ollama 兼容接口调用。
- 可以通过 `.env` 和 `config/sources.yaml` 控制开关、模型名称和超时。
- 当本地模型不可用时，系统仍会继续执行规则化的去重和基础摘要。

## 核心目录

- `app/api`: FastAPI 路由与接口模型。
- `app/cli`: Typer CLI 入口。
- `app/connectors`: GitHub、Reddit、Hacker News 来源接入。
- `app/services`: 抓取、去重、摘要、健康检查等核心逻辑。
- `app/repos`: 数据访问层。
- `app/models`: ORM 与领域模型。
- `app/worker`: 任务编排。
- `config`: 来源与策略配置。
- `docs`: 架构、数据模型、接口与来源说明。

## 后续扩展

- 接入调度器或容器定时任务。
- 新增 X/Twitter、ArXiv、RSS 等来源。
- 增加消息推送或前端展示层。
- 引入 embedding 模型以增强近似聚类能力。
