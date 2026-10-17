# Prometheus 告警与 Recording Rule · 核心规则库

> 改任何 rule 文件之前，**先读本文件**。
> 告警规则的第一原则：**每一条 firing 的告警，都必须有人能在 5 分钟内判断「现在要不要动」**。宁可少而准，不要多而吵。

---

## 一、Recording rule

作用：把昂贵查询预先算好存成新指标，**加速看板查询**，也方便告警复用同一份定义。

### 命名规则（必须遵守）

```
level:metric:operation
```

| 段 | 含义 | 示例 |
|---|---|---|
| level | 聚合层级 | `job` `instance` `service` `cluster` `dc` |
| metric | 源指标名（去掉 `_total` 后缀） | `requests` `request_duration_seconds` |
| operation | 操作描述，含时间窗 | `rate5m` `avg_over_time_5m` `sum` |

```yaml
groups:
  - name: http_requests_recording
    interval: 30s
    rules:
      - record: job:request_duration_seconds:avg5m
        expr: sum(rate(http_request_duration_seconds_sum[5m])) by (job)
              / sum(rate(http_request_duration_seconds_count[5m])) by (job)

      - record: cluster:http_requests:rate5m
        expr: sum(job:http_requests:rate5m) by (cluster)
```

要点：

- **冒号分隔的三段式**，冒号只允许出现在这里
- 输出指标的保留标签只能是 `level` 里声明的那些（`without` 或 `by` 控制），**别把 `instance` 带进 job 级指标**
- `record` 里**不要带 `_total`**（recording rule 的输出走 Gauge 语义）
- `interval` 默认取全局 `evaluation_interval`

---

## 二、告警规则标准写法

```yaml
groups:
  - name: service_availability
    rules:
      - alert: ServiceHighErrorRate
        expr: |
          sum by (job) (rate(http_requests_total{code=~"5.."}[5m]))
            / sum by (job) (rate(http_requests_total[5m]))
          > 0.05
        for: 5m
        labels:
          severity: critical
          team: backend
        annotations:
          summary: "{{ $labels.job }} 5xx 错误率超过 5%"
          description: "当前错误率 {{ $value | printf \"%.2f\" }}%，持续 5 分钟。"
          runbook_url: "https://wiki.example.com/runbook/service-high-error-rate"
```

| 字段 | 要求 |
|---|---|
| `alert` | 大驼峰，`<对象><症状>`，如 `ApiHighLatency`、`NodeDiskFillingUp` |
| `expr` | 必须返回**瞬时向量**；不能是标量、字符串或裸表名 |
| `for` | **必填**。抖动类 ≥ 2m，趋势类 ≥ 5m，磁盘预测类可 15m-1h |
| `labels.severity` | `critical` / `warning` / `info` 三档，别再发明第四档 |
| `labels.team` / `service` | 用于路由到正确的接收人 |
| `annotations.summary` | 一句话，包含 `$labels` |
| `annotations.description` | 包含当前值 `$value` 和判断依据 |
| `annotations.runbook_url` | 值班同学点进去就知道做什么 |
| `keep_firing_for` | 可选，让告警恢复后仍保持一段时间 firing 以通知修复完成 |

---

## 三、`for` 的正确理解

`for` 不是「首次满足后多久才发」，而是 **pending → firing 的持续时间要求**。

```
条件首次满足  → pending
持续满足到 for → firing
中途恢复      → 计时清零（回到 inactive）
```

经验值：

| 场景 | `for` 建议 |
|---|---|
| 瞬时抖动敏感（如实例掉线） | 1m-2m |
| 错误率、延迟类 | 5m |
| 资源水位（> 80%） | 10m-30m（避免每次扩容前的自然波峰告警） |
| 磁盘将满（线性预测） | 15m-1h |
| 缺失类（`absent`） | 2m-5m（`up` 抖动很常见） |

**两个极端都是错：**

- `for: 0s` 或不写 → 抖动即可触发，告警风暴
- `for: 1h` → 真故障都被拖到失效，等于没有告警

---

## 四、常见错误告警（逐条对照）

### 1. rate 窗口太短

```promql
# 错误：抓取间隔 30s，窗口只有 1m，只覆盖 2 个样本且边界剧烈抖动
rate(http_requests_total[1m]) > 100
```

**规则：`rate` 窗口 ≥ 4 × scrape_interval**。15s 抓取至少 `[1m]`，推荐 `[5m]`。

原因：窗口抖动会带来「数据不足 extrapolation」「counter reset 误判」两类误差，表现为曲线剧烈锯齿。

### 2. 对 Gauge 用 rate

```promql
# 错误：process_resident_memory_bytes 是 Gauge，rate 语义是错的
rate(process_resident_memory_bytes[5m]) > 1e9
```

Gauge 用 `max_over_time` / `avg_over_time` / 直接比较；`rate` 只对 Counter。

### 3. 用裸 Counter 差值

```promql
# 错误：不处理 counter reset，且依赖抓取时机
http_requests_total - http_requests_total offset 5m > 1000
```

用 `increase(http_requests_total[5m])`，它自动处理重置与外推。

### 4. 先 sum 再 rate

```promql
# 错误：多个 series 求和后再算速率，重置会把整段结果污染
rate(sum(http_requests_total)[5m:])
```

必须先 `rate` 再 `sum`：`sum(rate(http_requests_total[5m])) by (job)`。

### 5. sum 漏了 by

```promql
# 错误：所有 job 混成一个数，定位不到是谁
sum(rate(http_requests_total{code=~"5.."}[5m])) / sum(rate(http_requests_total[5m])) > 0.05
```

必须带上 `sum by (job)`，两侧 **by 的维度要一致**。

### 6. histogram_quantile 丢了 le

```promql
# 错误：by 里没有 le，分位数算不出来（返回 NaN 或常数）
histogram_quantile(0.99, sum(rate(http_request_duration_seconds_bucket[5m])) by (job))
```

必须 `sum by (le, job) (...)`。

### 7. 缺 for

漏掉 `for` 的告警几乎一定会在半夜把你叫醒：一次 GC 抖动、一次网络闪断都能触发 paging，值班同学很快就会把整个通道设为静音。

### 8. severity 全是 critical

分级失效 = 无人处理。只有「需要立即有人动手」的才是 critical。

### 9. 只告警不考虑「有没有意义」

```promql
# 错误：低于 100 条请求的时候，1 条错误就是 1%，一晚上响十次
error_rate > 0.01
```

必须加**最小样本量**条件：

```promql
sum by (job) (rate(http_requests_total{code=~"5.."}[5m]))
  / sum by (job) (rate(http_requests_total[5m])) > 0.05
and sum by (job) (rate(http_requests_total[5m])) > 1
```

### 10. 目标掉线检测用 `up == 0` 而不是 `absent`

`up == 0` 只能发现**已知的**目标。服务发现把实例摘掉后，`up` 这条 series 直接不存在，**没有 `up == 0` 可告警**。

```promql
# 检测某个 job 完全没有存活实例
absent(up{job="payment"} == 1)

# 检测 Prometheus 自己抓不到
absent(up)
```

### 11. 比率公式两侧单位不一致

```promql
# 错误：分子是 _bytes_total 的速率，分母是 Gauge 的瞬时值，比值没物理意义
rate(network_receive_bytes_total[5m]) / node_network_speed_bytes
```

### 12. 用 `irate` 做告警

`irate` 只看最后两个点，**极抖**。它适合画实时曲线，**不适合告警**。告警一律用 `rate`。

---

## 五、告警风暴抑制

三道闸门：

### 1. Alertmanager `inhibit_rules`（上游故障抑制下游）

```yaml
inhibit_rules:
  # 集群整体不可用时，抑制该集群内所有服务级告警
  - source_matchers: [alertname="ClusterDown", severity="critical"]
    target_match_re:
      alertname: ".*"
      cluster: "prod"
    equal: ["cluster"]
  # critical 抑制同名 warning
  - source_matchers: [severity="critical"]
    target_matchers: [severity="warning"]
    equal: ["alertname", "job"]
```

### 2. `group_by` 合并相似告警

```yaml
route:
  group_by: ['alertname', 'cluster', 'service']
  group_wait: 30s        # 等待同一组再聚合，避免第一条就单独发
  group_interval: 5m
  repeat_interval: 12h   # 没恢复的告警重复通知间隔
```

### 3. 分级推送：warning 只发群，critical 才打电话

```yaml
routes:
  - matchers: [severity="critical"]
    receiver: pagerduty
  - matchers: [severity="warning"]
    receiver: slack-ops
```

补充：`group_wait` 别设太小（会每条独立发），`repeat_interval` 别设太短（同一故障每小时打一次电话会把人打麻）。

---

## 六、Alertmanager 基本配置骨架

```yaml
global:
  resolve_timeout: 5m
route:
  receiver: default
  group_by: ['alertname', 'cluster']
  group_wait: 30s
  group_interval: 5m
  repeat_interval: 12h
  routes:
    - matchers: [severity="critical"]
      receiver: oncall
receivers:
  - name: oncall
    webhook_configs:
      - url: 'http://alert-gateway.example.com/hook'
inhibit_rules: []
```

调试命令：

```bash
promtool check rules /etc/prometheus/rules/*.yml
promtool test rules unit_test.yml     # 强烈建议：给核心告警写单测
amtool check-config /etc/prometheus/alertmanager.yml
amtool config routes show
```

---

## 七、告警单测（`promtool test rules`）

```yaml
rule_files:
  - alerts.yml
evaluation_interval: 1m
tests:
  - interval: 1m
    input_series:
      - series: 'http_requests_total{job="api",code="500"}'
        values: '0+10x10'
      - series: 'http_requests_total{job="api",code="200"}'
        values: '0+100x10'
    alert_rule_test:
      - eval_time: 10m
        alertname: ServiceHighErrorRate
        exp_alerts:
          - exp_labels: {severity: "critical", job: "api"}
            exp_annotations:
              summary: "api 5xx 错误率超过 5%"
```

> 上线告警前跑单测，是唯一能在半夜之前发现「表达式写反了」的办法。

---

## 八、上线前 Check List

- [ ] `promtool check rules` 通过
- [ ] 每条告警都有 `for`、`severity`、`summary`、`description`
- [ ] `rate`/`increase` 窗口 ≥ 4 × scrape_interval
- [ ] 比值类告警加了最小样本量条件
- [ ] 有 inhibit 规则覆盖「上游挂了导致下游全告警」
- [ ] `absent` 覆盖了「目标被摘掉」的情况
- [ ] 有 `promtool test rules` 单测
- [ ] 值班同学读 `summary` 就知道下一步做什么
