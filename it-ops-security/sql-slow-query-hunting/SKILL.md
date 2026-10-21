---
slug: sql-slow-query-hunting
name: 慢 SQL 定位与优化
displayName: "慢 SQL 定位与优化"
description: 慢 SQL 定位与优化：从慢日志/pg_stat_statements/性能 schema 取 TOP SQL，按总耗时排序。
version: 1.0.0
category: dev-programming
---

# 慢 SQL 定位与优化

## 触发场景
当用户的需求涉及：抓取慢查询；解读执行计划；优化；回归验证 时使用本技能。

### Step 1 · 抓取慢查询
从慢日志/pg_stat_statements/性能 schema 取 TOP SQL，按总耗时排序。

### Step 2 · 解读执行计划
EXPLAIN ANALYZE：找全表扫描、错误索引、行数估算偏差，逐条解读给用户听懂。

### Step 3 · 优化
手段顺序：改写 SQL → 加/改索引 → 结构调整（冗余/分区）。每步给出预期与验证方式。

### Step 4 · 回归验证
优化后重跑并对比耗时，记录到优化台账。

## 红线
- 索引建议必须说明写入代价
- 禁止未验证就宣称提速倍数
