---
name: prometheus-metrics-alert
slug: prometheus-metrics-alert-tianbao
displayName: Prometheus 指标命名与告警规则设计
display_name: "Prometheus 指标命名与告警规则设计"
display_name_en: "Prometheus Metric Naming and Alerting Rule Design"
version: "1.0.0"
summary: 写 exporter 前先定取名：namespace_subsystem_name_unit_suffix 全小写下划线、Counter 必须 _total 而 Gauge 绝不许、单位一律基本单位（_seconds 不写 ms、_bytes 不写 MB）、环境和集群只能进 label 不能进名字；label 基数陷阱给出 series 数等于各标签取值笛卡尔积的算法与 user_id / order_id / 原始 url / errorMessage 等黑名单标签给出对等替代路径（trace 系统、路径模板、日志 + 有限枚举）；四种指标类型选型判定树、Histogram 三件套与 bucket 必须覆盖真实分布（否则 p99 算出来是假的）、Recording rule 的三段式命名 level:metric:operation；告警侧逐条对照 12 类常见错误（rate 窗口必须 ≥ 4 倍抓取间隔、先 sum 再 rate、Gauge 误用 rate、histogram_quantile 丢了 le、比值告警没加最小样本量、用 up==0 检测不到目标被摘掉要用 absent、irate 不适合告警、缺 for 或 for 过长），配 Alertmanager inhibit_rules 与 group_by 抑制告警风暴，配脚本静态校验指标命名与告警规则。
description: 要给 Prometheus 定指标名、写 exporter、写告警规则或 recording rule、担心 label 基数把存储打爆、告警太多不敢值班时使用。当用户说"指标该怎么命名""label 能不能用 user_id""series 数太多怎么办""这条告警为什么半夜乱响""rate 窗口应该写多长""for 写成多少合适""p99 算出来是不是真的""recording rule 怎么命名""目标被摘掉了为什么没有告警""怎么避免告警风暴"时使用。内置单位后缀表与反例对照、保留禁用字（le / quantile / job / instance）、四种类型选型判定、Histogram 与 Summary 的取舍与不可跨实例聚合的红线、桶设计与 le 保留、告警模板八段字段要求、for 的经验取值表、12 类错误告警的错误写法与正确写法对照、inhibit_rules 与 group_by 抑制方案、promtool test rules 单测骨架，配 scripts/prometheus_rules_check.py 解析 Prometheus rule yaml 与 /metrics 抽取输出，按严重/错误/警示/提示分级输出命名与告警规则问题。适用于后端研发、SRE 与可观测性平台工程师。
license: Apache-2.0
author: 刘天宝｜墨燊
category: it-ops-security
subCategories:
  - itops-monitoring
icon: icon.svg
tags: [Prometheus, 指标命名, 告警规则, Recording Rule, PromQL, label基数, Histogram, 告警风暴抑制, 可观测性, SRE]
language: zh-CN
visibility: public
---

# Prometheus 指标命名与告警规则设计（prometheus-metrics-alert）

指标名一旦上线就是 API：**改名等于让所有看板与告警同时失效。**

这个技能做三件事：**定名字** → **控基数** → **写准告警**。

---

## 硬边界（先看这条）

| 能做 | 不能做 |
|---|---|
| 给出命名、类型、单位的判定规则 | ❌ 替你决定「该不告警」（这是业务决策） |
| 静态检查 rule 文件与指标清单 | ❌ 替代 `promtool check rules` / `amtool check-config` |
| 量化 label 基数与估算 series 数 | ❌ 算出准确的内存占用（受 chunk、head block、压缩影响） |
| 给出告警抑制与分级方案 | ❌ 直接修改线上 Alertmanager 配置 |

**以下情况必须停下来先做人工确认：**
- 存量指标要改名 → 必须走双写过渡，先加新指标、再迁看板、最后删旧指标
- 单个 `series` 数已到百万级 → 先做容量核算，别再加高基数标签
- 告警要作为值班依据 → 必须先在灰度通道跑一个迭代

---

## 一、什么时候用这个技能

| 用户这样说 | 就用 |
|---|---|
| "这个指标该怎么命名" | ✅ |
| "label 能不能用 user_id" | ✅ |
| "series 数爆了怎么办" | ✅ |
| "用 Counter 还是 Gauge" | ✅ |
| "p99 为什么算出来不对" | ✅ |
| "rate 窗口该写多长" | ✅ |
| "告警为什么半夜乱响" | ✅ |
| "recording rule 怎么命名" | ✅ |
| "目标被摘了为什么没告警" | ✅ |
| "怎么抑制告警风暴" | ✅ |

---

## 二、完整工作流

```
第 1 步  读规则文件 rules/metrics_naming.md 与 rules/alert_rules.md
第 2 步  写 exporter 前先过一次命名检查清单（metrics_naming.md 第六节）
第 3 步  导出指标样本，跑命名与基数体检
         curl http://app:8080/metrics > scrape.txt
         python scripts/prometheus_rules_check.py --kind metrics --file scrape.txt
第 4 步  写完 rule 文件，跑规则体检
         python scripts/prometheus_rules_check.py --kind rules --file alerts.yml --scrape-interval 15
第 5 步  必跑官方校验（脚本无法替代）
         promtool check rules alerts.yml
         promtool test rules unit_test.yml
第 6 步  配 Alertmanager：inhibit_rules + group_by + 分级路由
第 7 步  灰度一个迭代，统计 firing 次数与「是不是需要动手」的比例，再调整 for 与阈值
```

---

## 三、命名：一句话规则

```
namespace_subsystem_name_unit_suffix     全小写 + 下划线
```

**四条最常犯的错：**

| 错误 | 原因 | 正确 |
|---|---|---|
| `httpRequestCount` | 驼峰 + 无单位 | `http_requests_total` |
| `request_latency_ms` | 用了毫秒 | `request_duration_seconds` |
| `prod_redis_used_memory_total` | 环境进名字 + Gauge 用 `_total` | `redis_used_memory_bytes{env="prod"}` |
| `queue_length_count` | Gauge 冒充 count | `queue_length` |

**记住两条：**
- `_total` 是 **Counter 专用**，Gauge 绝不能用
- 单位一律基本单位：`_seconds`、`_bytes`、`_ratio`（0-1）
- 环境、集群、机房、实例来源都是 **label**，不能进名字
- `le` / `quantile` / `job` / `instance` 是**保留标签**，别自定义同名的东西

完整的单位后缀表（含 `_info`、`_created`、`_bucket` / `_sum` / `_count`）在 `rules/metrics_naming.md` 第二节。

---

## 四、四种类型怎么选

```
会不会下降？                 → 会：Gauge
是不是累计的量？             → 是：Counter
要不要分析延迟分布 / 算 p99？ → 要：Histogram
需要极高精度且只有一个实例？   → Summary（否则 Histogram）
```

**Summary 的红线**：客户端算好的 quantile **不可跨实例聚合**，对 `quantile` 求 sum / avg 得到的数没有意义。要多实例统一看分布就必须用 Histogram。

**Histogram 的两个硬检查：**
- 必须有 `le="+Inf"` 桶（`histogram_quantile` 依赖它做分母）
- 桶必须覆盖真实分布：**p99 是 800ms 而最大桶是 0.5s，算出来的 p99 永远不超过 0.5s**

```promql
# 正确
histogram_quantile(0.99, sum by (le, job) (rate(http_request_duration_seconds_bucket[5m])))
# 错误：by 里没有 le，分位数直接算不出来
```

---

## 五、label 基数：series 数是乘法

```
series 数 = Π |每个标签的取值数|
```

| 标签 | 取值 | 结果 |
|---|---|---|
| `method`(5) × `status`(10) | 50 | 50 × 实例数，健康 |
| `method` × `status` × `url`（含 id） | 5 × 10 × 100000 | **500 万**，直接把 Prometheus 打挂 |

**黑名单标签**（几乎永远不该进 label）：`user_id` `order_id` `request_id` `trace_id` `session_id` `uuid` `email` `phone` `ip` `原始 url` `error_message` `timestamp`。

想要「看某个用户」就去查 **trace 系统**；想要「看某个 URL 的耗时」就把它变成路径模板 `route="/api/order/:id"`；错误详情打日志，`_total{reason="timeout"}` 只保留有限枚举。

---

## 六、告警：写之前先看这 12 类错误

完整对照（含错误写法 vs 正确写法）在 `rules/alert_rules.md` 第四节。**最常见的四条：**

**① rate 窗口太短。** 窗口必须 **≥ 4 × scrape_interval**：15s 抓取至少 `[1m]`，推荐 `[5m]`。窗口太短会因为样本不足导致外推误差与 counter reset 误判，曲线锯齿，告警乱响。

**② 缺 `for`。** 一次 GC 抖动就能 paging。经验值：抖动类 1-2m、错误率/延迟类 5m、资源水位 10-30m、磁盘预测 15m-1h。**两个极端都错**：`for: 0s` 是告警风暴，`for: 1h` 等于没告警。

**③ 比值告警没加最小样本量。** 100 条请求里错 1 条就是 1%，一晚上响十次：

```promql
错误率/总量 > 0.05
and 总请求速率 > 1        # 必须加这一条兜底
```

**④ 用 `up == 0` 检测目标掉线。** 服务发现把实例摘掉后，`up` 这条 series 直接不存在，**根本没有 `up == 0` 可以告警**。要用：

```promql
absent(up{job="payment"} == 1)
```

**其它必查**：Gauge 误用 `rate`、用裸 Counter 差值而不是 `increase`、先 `sum` 再 `rate`（顺序反了）、`histogram_quantile` 丢了 `le`、两侧 `by` 维度不一致、用 `irate` 做告警（只看最后两个点，极抖）。

---

## 七、抑制告警风暴：三道闸门

| 闸门 | 做法 | 关键参数 |
|---|---|---|
| 抑制 | `inhibit_rules`：上游故障抑制下游告警 | 用 `source_matchers` + `equal` |
| 合并 | `route.group_by` + `group_wait` | `group_wait: 30s`、`group_interval: 5m` |
| 分级 | critical 打电话、warning 只发群 | `repeat_interval: 12h` |

```yaml
inhibit_rules:
  - source_matchers: [alertname="ClusterDown", severity="critical"]
    target_match_re: {cluster: "prod"}
    equal: ["cluster"]
```

---

## 八、Recording rule 命名

```
level:metric:operation
job:http_requests:rate5m
cluster:request_duration_seconds:avg5m
```

- 三段式，**冒号只允许出现在这里**（exporter 不要用冒号）
- 输出里**不要带 `_total`**
- `by` 要跟 `level` 对齐：job 级指标别把 `instance` 带进去

---

## 九、脚本用法

```bash
# 体检 /metrics 抽取的命名与 label 基数
curl http://app:8080/metrics > scrape.txt
python scripts/prometheus_rules_check.py --kind metrics --file scrape.txt

# 体检 prometheus rule 文件
python scripts/prometheus_rules_check.py --kind rules --file alerts.yml --scrape-interval 15

python scripts/prometheus_rules_check.py --selftest
```

| 参数 | 说明 |
|---|---|
| `--kind` | `metrics`（/metrics 文本）/ `rules`（rule yaml）/ `auto`（默认自动识别） |
| `--file` | 待检查文件；省略则 `--selftest` |
| `--scrape-interval` | 抓取间隔（秒），用于判定 `rate` 窗口是否过短，默认 15 |
| `--max-series` | 单指标 series 告警阈值，默认估算用 10000 |
| `--json` / `--out` | JSON 输出 / 指定输出文件 |
| `--selftest` | 跑内置自检 |

**体检输出四段：**

1. **指标命名**：Gauge 误用 `_total`、驼峰或非法字符、用了毫秒等非基本单位、黑名单标签、缺 `_count`/`_sum`/`_bucket` 三件套、histogram 缺 `+Inf` 桶
2. **基数风险**：按标签取值估算 series 数并给出上限告警
3. **告警规则**：缺 `for`、`for` 过短/过长、`rate`/`increase` 窗口 < 4×抓取间隔、缺 `severity`、缺 `summary`/`description`、`absent` 误用 `up == 0`、先 sum 再 rate、`histogram_quantile` 丢 `le`、`irate` 用于告警、两侧 `by` 维度不一致
4. **Recording rule**：命名不符合 `level:metric:operation`、输出名带 `_total`

> 脚本是**静态检查**，不是 `promtool` 的替代品。**上线前必须跑 `promtool check rules`。**

---

## 十、人工确认清单（这步不能省）

- [ ] 每个 Counter 都以 `_total` 结尾，每个 Gauge 都不带
- [ ] 单位全部是基本单位（秒 / 字节 / 比值）
- [ ] 没有任何黑名单标签；`_bucket` 系列带 `le` 且有 `+Inf`
- [ ] `promtool check rules` 通过
- [ ] `rate` 窗口 ≥ 4 × scrape_interval
- [ ] 每条告警都有 `for`、`severity`、`summary`、`description`、`runbook_url`
- [ ] 比值类告警加了最小样本量兜底
- [ ] `absent` 覆盖了「目标被摘掉」的场景
- [ ] 有 `inhibit_rules` 覆盖上游故障
- [ ] 灰度观察过一个完整迭代的实际 firing 情况

---

## 十一、最常见的坑

**坑一：指标上线了才发现名字起错。**
指标名就是 API。改成 `http_requests_total` 以后，所有看板、告警、SLO 查询全部失效。正确做法：**发布前就按命名规则过一遍**；已经上线就走双写过渡。

**坑二：把 `user_id` 当 label。**
上线 3 天后 series 数从 5 万涨到 500 万，Prometheus OOM。**这类需求属于 trace，不属于 metrics。**

**坑三：以为 `_total` 只是个习惯。**
`_total` 是 Counter 的语义标记。`process_resident_memory_bytes_total` 这种名字会让人用 `rate()` 去算内存的增长率，而它根本不是 Counter。**命名错了，查询就错了。**

**坑四：`rate(...[1m])`。**
抓取 15s 时窗口只覆盖 4 个样本，边界处的外推让曲线剧烈锯齿，告警随机触发。窗口至少取 **4 倍抓取间隔**，`[5m]` 是最常见的稳妥值。

**坑五：`histogram_quantile` 的 `by` 里没有 `le`。**
返回一堆无意义的数，而且**不报错**。同样的写法如果忘了 `le`，看板上会出现一条平得可疑的曲线。

**坑六：桶的最大值是 0.5s，业务 p99 是 800ms。**
算出来的 p99 永远 ≤ 0.5s。**这是最危险的假数据**——它看起来完全正常，只是永远不报警。

**坑七：告警加了 `for: 30m` 为了「别吵」。**
真故障也要半小时后才通知，等于这条告警失效。要降噪应该改**阈值、加最小样本量、用 inhibit**，而不是拉长 `for`。

**坑八：所有告警都是 `severity: critical`。**
分级的意义就是「哪些现在必须动手」。全是 critical 的结果是整个通道被静音。

**坑九：只用 `up == 0` 做实例掉线告警。**
节点摘掉、服务发现删除后，`up` series 消失，告警条件再也命中不了。必须配 `absent()`。

**坑十：Summary 跨实例求平均。**
`avg(instance_processing_seconds{quantile="0.99"})` 得到的数在数学上就是错的；多实例场景只能用 Histogram。

---

## 十二、边界与免责

- 本技能给出的是**静态检查与规则建议**，不构成对线上监控有效性的保证
- series 数与内存占用的真实关系受 chunk 编码、head block、压缩、保留策略共同影响，**以实际监控（`prometheus_tsdb_head_series`）为准**
- 告警阈值必须由业务方确认，脚本无法判断「这条告警要不要 paging」
- Prometheus 与 Alertmanager 的字段在不同版本存在差异（如 `matchers` 取代 `match`/`match_re`），**操作前确认版本**

---

## 十三、许可

本技能由 **刘天宝｜墨燊** 原创，采用 **Apache License 2.0**。

`rules/` 中的命名约定与告警写法基于 Prometheus 官方文档与社区最佳实践整理，不同版本存在差异，请以官方文档为准。
