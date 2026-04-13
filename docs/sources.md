# 来源说明

## GitHub

- 使用 GitHub REST API 的仓库搜索接口。
- 通过关键词查询 AI 相关仓库。
- 支持可选 watchlist 仓库的 release 抓取。
- 推荐通过 `GITHUB_TOKEN` 提高额度。

## Reddit

- 使用公开 JSON 端点或官方 API 读取子版块。
- v1 关注：
  - `r/MachineLearning`
  - `r/LocalLLaMA`
  - `r/singularity`
- 通过外链、标题、发布时间和来源分数参与去重和排序。

## Hacker News

- 使用 Algolia 提供的 HN Search API。
- 通过关键词搜索 `story`。
- 保存 `points` 与 `num_comments` 作为来源侧热度信号。

## X / Twitter 预研结论

- v1 不直接接入。
- 原因：
  - 官方 API 成本高。
  - 非官方抓取稳定性和合规风险高。
  - 转发、引用和搬运内容导致重复率高。
- 后续接入建议：
  - 优先提取外链，以 `normalized_url` 做第一层聚合。
  - 过滤 retweet 和 quote-only 内容。
  - 对无外链推文按作者、发布时间窗口和文本相似度做二次去重。
  - 单独配置更严格的速率限制和失败重试。
