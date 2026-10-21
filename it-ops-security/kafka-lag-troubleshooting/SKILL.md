---
slug: kafka-lag-troubleshooting
name: 消息队列积压排查
displayName: "消息队列积压排查"
description: 消息队列积压排查：采集各 topic/partition lag、消费组状态、消费 TPS、消息产生速率，判断积压增速。
version: 1.0.0
category: it-ops-security
---

# 消息队列积压排查

## 触发场景
当用户的需求涉及：确认现状；定位原因；应急处理；长期改进 时使用本技能。

### Step 1 · 确认现状
采集各 topic/partition lag、消费组状态、消费 TPS、消息产生速率，判断积压增速。

### Step 2 · 定位原因
检查：消费者是否存活、消费逻辑是否变慢（外部调用超时）、分区倾斜（热点 key）、rebalance 风暴。

### Step 3 · 应急处理
方案：扩容消费者（≤分区数）、临时跳过毒消息（记录到死信）、降级消费逻辑，给出操作步骤。

### Step 4 · 长期改进
告警阈值建议、消费幂等改造、容量规划。

## 红线
- 跳过消息必须先落死信队列可回放，禁止直接丢弃
- 扩容受分区数上限约束，先说明再操作
