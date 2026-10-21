---
slug: etl-idempotent-rerun
name: ETL 幂等重跑
displayName: "ETL 幂等重跑"
description: ETL 幂等重跑：画出任务依赖图，标注每个任务：输入源、输出表、写入模式（append/overwrite/merge）。
version: 1.0.0
category: data-analysis
---

# ETL 幂等重跑

## 触发场景
当用户的需求涉及：梳理管道；设计幂等策略；重跑演练；输出规范 时使用本技能。

### Step 1 · 梳理管道
画出任务依赖图，标注每个任务：输入源、输出表、写入模式（append/overwrite/merge）。

### Step 2 · 设计幂等策略
append 改 merge/分区覆盖；加业务幂等键；记录水位线支持断点重跑。

### Step 3 · 重跑演练
在测试环境模拟：失败重跑、历史补数、并发重跑，验证数据一致（行数+校验和对账）。

### Step 4 · 输出规范
管道改造清单与重跑操作手册。

## 红线
- 禁止裸 append 无幂等键的历史补数
- 生产重跑前必须先备份目标分区
