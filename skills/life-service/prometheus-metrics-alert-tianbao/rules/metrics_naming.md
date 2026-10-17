# Prometheus 指标命名规范 · 核心规则库

> 写任何 exporter、任何 rule 文件之前，**先读本文件**，不要凭印象定名字。
> 指标名一旦上线就是 API：**改名等于让所有看板与告警同时失效。**

---

## 一、命名基本语法

```
namespace_subsystem_name_unit_suffix
```

实例：

```
http_server_requests_duration_seconds_bucket   # namespace=http, subsystem=server
process_resident_memory_bytes                 # Prometheus 内置风格
kafka_topic_partitions                        # 无单位的 Gauge，不加后缀
node_disk_io_time_seconds_total               # Counter，必须 _total
```

| 规则 | 说明 |
|---|---|
| 字符集 | 指标名 `[a-zA-Z_:][a-zA-Z0-9_:]*`；标签名 `[a-zA-Z_][a-zA-Z0-9_]*` |
| 大小写 | **全部小写**，下划线分词，不要用驼峰 |
| 冒号 | 只允许出现在 recording rule 产生的指标名里，exporter **不要用** |
| 命名空间 | 同一 exporter 统一前缀（如 `mysql_`、`redis_`、`myapp_`） |

**保留禁用：**

| 保留字 | 说明 |
|---|---|
| `le` | histogram 的 bucket 上界标签，别当普通标签用 |
| `quantile` | summary 的分位数标签 |
| `__name__` | 内部使用 |
| `job` / `instance` | Prometheus 自动附加，不要自己 exporter 再打一遍 |

---

## 二、单位后缀表

| 后缀 | 含义 | 示例 |
|---|---|---|
| `_seconds` | 秒（**基本单位，不用毫秒**） | `request_duration_seconds` |
| `_bytes` | 字节 | `response_size_bytes` |
| `_bytes_total` | 字节累计流量（Counter） | `network_transmit_bytes_total` |
| `_total` | Counter 累计计数 | `http_requests_total` |
| `_created` | Gauge 型的时间戳（秒），跟随同名 Counter | `http_requests_created` |
| `_count` | histogram/summary 的样本数 | `request_duration_seconds_count` |
| `_sum` | histogram/summary 的总和 | `request_duration_seconds_sum` |
| `_bucket` | histogram 的分桶 | `request_duration_seconds_bucket{le="0.3"}` |
| `_ratio` | 比值，取值 0-1 | `cache_hit_ratio` |
| `_percent` | 百分比 0-100（不推荐，优先 `_ratio`） | |
| `_kelvin` / `_celsius` | 温度基本单位 | `process_cpu_celsius` |
| `_info` | 元数据，**值恒为 1** | `node_uname_info{release="..."} 1` |
| `_timestamp_seconds` | Unix 时间戳（Gauge） | `last_run_timestamp_seconds` |

**禁止：**

- ❌ 用 `ms` / `milliseconds` 做后缀（违反基本单位原则）
- ❌ 给 Gauge 加 `_total`（`_total` 是 Counter 专用）
- ❌ 名字里带环境、集群名、机房名（这些是 **label**，不是名字）
- ❌ 名字里带 `_count` 但其实是 Gauge

**反例对照：**

| 错误 | 原因 | 正确 |
|---|---|---|
| `httpRequestCount` | 驼峰 + 无单位 | `http_requests_total` |
| `request_latency_ms` | 用了毫秒 | `request_duration_seconds` |
| `prod_redis_used_memory_total` | 环境进了名字 + Gauge 用了 total | `redis_used_memory_bytes{env="prod"}` |
| `queue_length_count` | Gauge 冒充 count | `queue_length` |

---

## 三、四种指标类型选型

| 类型 | 语义 | 适合 | 不适合 | 常用函数 |
|---|---|---|---|---|
| **Counter** | 只增不减的累计值 | 请求数、错误数、发送字节数 | 任何会下降的量 | `rate` `increase` `irate` |
| **Gauge** | 可增可减的瞬时值 | 队列长度、内存占用、在线人数、温度 | 累计计数 | `avg_over_time` `max_over_time` `delta` `deriv` |
| **Histogram** | 服务端分桶，可聚合、可算任意分位数 | 请求耗时、响应体大小 | 需要精确分位数且能接受开销的场景 | `histogram_quantile` `rate(..._bucket[5m])` |
| **Summary** | 客户端算好分位数，不可跨实例聚合 | 单实例 SLO、对精度要求极高 | **多实例聚合**（禁止对 quantile 求 sum/avg） | 直接读 quantile |

**选型判定：**

```
会不会下降？                 → 会：Gauge
是不是累计的量？             → 是：Counter
要不要分析延迟分布 / 算 p99？ → 要：Histogram
需要极高精度且只有一个实例？   → Summary（否则 Histogram）
```

**为什么不要自己上报平均值**：`avg(f(x))` 不可再聚合——两个实例的平均再平均是错的。延迟这类分布必须上报 Histogram（或 Summary），让 Prometheus 算分位数。

---

## 四、Histogram 三件套与 bucket 设计

一个 histogram 会导出**三个指标**（用 `_bucket` / `_sum` / `_count` 后缀）：

```
http_request_duration_seconds_bucket{le="0.05"} 1234
http_request_duration_seconds_bucket{le="0.1"}  2400
http_request_duration_seconds_bucket{le="+Inf"} 5000
http_request_duration_seconds_sum                123.4
http_request_duration_seconds_count              5000
```

**硬性检查：**

- 必须有 `le="+Inf"` 桶（`histogram_quantile` 依赖它作为分母）
- 桶必须**覆盖真实分布**：如果 p99 是 800ms，而最大桶是 0.5s，算出来的 p99 **永远不超过 0.5s**（假的）
- 桶数量建议 ≤ 20 个；每加一个桶 = 多一条 series

```promql
# 正确的 p99 算法
histogram_quantile(0.99,
  sum by (le, job) (rate(http_request_duration_seconds_bucket[5m]))
)

# 平均耗时（用 _sum / _count，不要用 bucket 估算）
sum(rate(http_request_duration_seconds_sum[5m]))
  / sum(rate(http_request_duration_seconds_count[5m]))
```

> 注意 `by (le, ...)`：**丢了 `le` 就完全没法算分位数**，这是最常见的 histogram 错误。

---

## 五、标签基数陷阱（最容易把 Prometheus 打挂）

**series 数量 = 各标签取值数的笛卡尔积。**

```
series 数 = Π |标签取值|  （每个指标 × 每个 job × 每个 instance 各算一遍）
```

| 指标 | 标签数 | 每标签取值 | series 数 |
|---|---|---|---|
| `http_requests_total{method,status}` | 2 | 5 × 10 | 50 × 实例数 |
| `http_requests_total{method,status,url}`（url 含 id） | 3 | 5 × 10 × 100000 | **500 万 × 实例数** |

**黑名单标签**（几乎永远不该做 label）：

```
user_id / uid / order_id / request_id / trace_id / session_id
uuid / guid / email / phone / ip / mac
url（含路径参数的原始 URL）/ referer / cookie
timestamp / date（变成长时间序列）
error_message / stacktrace（任意字符串）
k8s pod_name（含随机后缀）
```

**替代做法：**

| 想做的事 | 错误 | 正确 |
|---|---|---|
| 看某个用户 | `label user_id` | 换 **trace** 系统（Jaeger / Tempo） |
| 看某个 URL 的耗时 | `label url`（原始） | `label route="/api/order/:id"`（路径模板） |
| 看错误详情 | `label error_message` | 打点到日志，`_total{reason="timeout"}` 用有限枚举分类 |

**健康的参考量级**（不是硬限制，取决于内存与抓取间隔）：

| 维度 | 参考值 |
|---|---|
| 单指标 series 数 | < 1 万，超过就该拆 |
| 单个 exporter 端点 | < 1 万 series 较舒适 |
| 单 Prometheus 实例 | 百万级 series 是常见工程上限参考，需按内存核算 |
| 单个指标标签数 | ≤ 8 个；每多 1 个高基数标签都是乘法 |
| 标签取值长度 | 短；超长字符串直接吃内存 |

自查 PromQL：

```promql
# 找出 series 最多的前 10 个指标
topk(10, count by (__name__) ({__name__=~".+"}))

# series 总数
count({__name__=~".+"})
```

---

## 六、命名 Check List（写 exporter 时逐条核）

- [ ] 名字全小写、下划线分词
- [ ] Counter 以 `_total` 结尾；Gauge 不带 `_total`
- [ ] 单位用基本信息单位（`_seconds` 不是 `_ms`，`_bytes` 不是 `_mb`）
- [ ] `_ratio` 取值在 0-1，`_percent` 在 0-100，不混用
- [ ] 同一个「东西」在不同 exporter 里用同一个名字（如 `http_requests_total`）
- [ ] 环境、集群、机房、实例来源都进了 label，不在名字里
- [ ] 没有任何黑名单标签
- [ ] histogram 有 `+Inf` 桶
- [ ] summary 不跨实例聚合
- [ ] `_info` 指标的值恒为 1，信息装在 label 里
