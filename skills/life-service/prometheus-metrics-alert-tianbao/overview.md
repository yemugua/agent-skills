# Prometheus 指标命名与告警规则设计 · 能力概览

## 你会得到什么

**指标命名可以直接照着落地**。`namespace_subsystem_name_unit_suffix` 全小写下划线分词，附完整的单位后缀表（`_total` / `_count` / `_sum` / `_bucket` / `_info` / `_created` / `_ratio` / `_seconds` / `_bytes`）和四条高频错误的反例对照：`httpRequestCount` → `http_requests_total`、`request_latency_ms` → `request_duration_seconds`、`prod_redis_used_memory_total` → `redis_used_memory_bytes{env="prod"}`、`queue_length_count` → `queue_length`。保留禁用字（`le` / `quantile` / `job` / `instance`）也标了出来。

**label 基数陷阱算得清楚**。series 数等于各标签取值数的笛卡尔积，`method` × `status` 是 50 条，加上含 id 的原始 url 就是 500 万条。给出 `user_id` / `order_id` / `request_id` / `trace_id` / `uuid` / `email` / `ip` / 原始 url / `error_message` / `timestamp` 黑名单，以及每条需求的正确落点：查用户去 trace 系统、查 URL 改路径模板 `route="/api/order/:id"`、查错误详情打日志只保留有限枚举。

**四种指标类型有判定树，Histogram 的红线写死**。会不会下降决定 Counter 还是 Gauge，要不要算 p99 决定 Histogram，Summary 明确标注「quantile 不可跨实例聚合」这条不可碰的红线。Histogram 两个硬检查：必须有 `le="+Inf"` 桶，且桶必须覆盖真实分布——最大桶 0.5s 而真实 p99 是 800ms 时，算出来的 p99 永远不超过 0.5s，这是最危险的假数据。

**12 类错误告警有错误写法与正确写法对照**。rate 窗口必须 ≥ 4 倍抓取间隔、Gauge 不能误用 rate、要用 `increase` 而不是裸 Counter 差值、必须先 `rate` 再 `sum`、`histogram_quantile` 的 `by` 里必须有 `le`、比值告警必须加最小样本量兜底、目标掉线要用 `absent()` 而不是 `up == 0`、`irate` 不适合告警。`for` 给出了分场景经验取值（抖动 1-2m、错误率 5m、资源水位 10-30m、磁盘预测 15m-1h），并指出两个极端都是错。

**告警风暴三道闸门**：Alertmanager `inhibit_rules` 抑制上游故障、路由 `group_by` + `group_wait` 合并相似告警、`severity` 分级推送。附 `promtool test rules` 单测骨架——上线前跑单测是发现表达式写反的唯一办法。

**脚本**：`scripts/prometheus_rules_check.py` 两种模式。体检 `/metrics` 文本时检查 Gauge 误用 `_total`、非基本信息单位、黑名单标签、histogram 三件套缺失与 `+Inf` 桶缺失，并估算 series 数；体检 rule yaml 时检查缺 `for`、`for` 过短或过长、`rate`/`increase` 窗口不足、缺 `severity`、缺 `summary`/`description`、`absent` 使用不当、先 sum 再 rate、`histogram_quantile` 丢 `le`、`irate` 用于告警、`by` 维度不一致、recording rule 命名不符合 `level:metric:operation`。

## 典型用法

1. 写 exporter 前：先过命名检查清单，再拿 `/metrics` 样例跑脚本体检。
2. 告警上线评审：跑规则体检 + `promtool check rules` + `promtool test rules` 三件套餐。
3. 值班被吵：按「缺 for / 缺最小样本量 / 缺 inhibit / 阈值不合理」四类快速定位。
4. 存储膨胀：跑 `/metrics` 体检看哪个标签进了黑名单。

## 边界

- 静态检查不能替代 `promtool check rules`，上线前必须跑官方校验
- series 数与内存占用的真实关系受 chunk 编码、head block 与压缩影响，以 `prometheus_tsdb_head_series` 实测为准
- 告警阈值是业务决策，脚本只能查形式问题
- Prometheus 与 Alertmanager 字段在不同版本有差异，`matchers` 取代 `match`/`match_re`，操作前确认版本
