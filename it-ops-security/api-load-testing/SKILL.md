---
slug: api-load-testing
name: API Load Testing 接口压测助手
description: 根据接口文档或 curl 示例，用 hey/wrk/ab/locust 设计并执行负载测试，输出 P95/P99 延迟、吞吐量、错误率报告与瓶颈建议。触发词：压测、性能测试、QPS、并发测试、负载测试。
displayName: "API Load Testing 接口压测助手"
version: 1.0.0
category: dev-programming
---

# API Load Testing — 接口压测助手

## 触发场景
- "帮我压一下这个接口"、"QPS 能到多少"、"上线前做性能测试"

## 工作流程

### Step 1 · 明确测试目标（缺就问）
1. 目标接口（URL / 方法 / 认证方式 / 请求体）
2. 关键问题：**性能验收线**（如 P95 < 200ms、错误率 < 0.1%）？还是找极限容量？
3. 负载模型：阶梯加压（找拐点）还是固定并发（验证达标）？

### Step 2 · 选择并准备工具
按可用性依次选：`hey`（轻量首选）→ `ab` → `wrk`（高并发）→ Python locust（复杂场景/带逻辑）。
```bash
# 阶梯加压示例（hey）
for c in 10 50 100 200 500; do
  hey -z 30s -c $c -H "Authorization: Bearer $TOKEN"       -H 'Content-Type: application/json'       -d '{"q":"test"}' https://api.example.com/search       | grep -E "Requests/sec|Latency distribution|p95|p99" | sed "s/^/c=$c /"
done
```
注意：写测试数据文件时用工作区路径，避免污染项目目录。

### Step 3 · 执行与数据纪律
- 先小并发冒烟（c=1，10s）确认接口可用、参数正确，再正式压
- 每档至少 30s；档间留 10~30s 冷却
- **只对有授权的目标压测**——用户自有的服务；拒绝压测第三方/线上他人服务
- 记录环境：压测机规格、服务部署位置（同机房/跨网）、并发档位

### Step 4 · 输出报告
```markdown
# 压测报告：POST /api/search（2026-10-06）
| 并发 | RPS | P50 | P95 | P99 | 错误率 |
|---|---|---|---|---|---|
| 50  | 812 | 45ms | 110ms | 180ms | 0% |
- 结论：拐点出现在 c=200（RPS 不再上升，P95 翻倍）
- 瓶颈推断与建议：…（基于数据，不臆测）
```
- 建议方向：慢查询/缺索引、连接池、缓存、序列化开销、GC——给验证方法而非直接下结论

## 红线
- 严禁对非授权目标压测；发现目标是公网第三方服务立即停止并确认
- 报告必须基于实际输出数据，禁止估算冒充实测值
