---
slug: adr-writer
name: ADR Writer 架构决策记录助手
description: 架构决策记录（ADR）编写助手。当团队做出技术选型、架构变更、引入新依赖等决策时，生成符合 MADR 格式的 ADR 文档，维护 docs/adr/ 决策序列，支持检索历史决策。触发词：ADR、架构决策、技术选型记录、决策记录。
displayName: "ADR Writer 架构决策记录助手"
version: 1.0.0
category: dev-programming
---

# ADR Writer — 架构决策记录助手

## 触发场景
- 团队做出技术选型（数据库、框架、消息队列等）需要留档
- 架构变更、接口规范调整、引入/淘汰依赖
- 用户说"记录一下这个决策"、"写个 ADR"、"为什么当初选 X"

## 工作流程

### Step 1 · 收集决策要素
向用户确认（缺什么问什么，不要编造）：
1. **决策标题**：动宾结构，如"采用 PostgreSQL 替换 MongoDB"
2. **状态**：proposed（提议）/ accepted（已接受）/ deprecated（已废弃）/ superseded（被取代）
3. **背景**：为什么现在要做这个决策，面临什么问题
4. **候选方案**：至少 2 个，各列优劣
5. **决策结果与理由**：为什么选它
6. **后果**：正面/负面影响、需要跟进的事项

### Step 2 · 编写 ADR（MADR 格式）
写入 `docs/adr/NNNN-<短标题>.md`，编号四位递增（查看目录取最大编号 +1）：

```markdown
# NNNN. {标题}

- 状态：{proposed|accepted|deprecated|superseded by NNNN}
- 日期：YYYY-MM-DD

## 背景（Context）
{面临的问题与约束}

## 候选方案（Options）
### 方案 A：{名称}
- 优点：…
- 缺点：…

### 方案 B：{名称}
…

## 决策（Decision）
选择方案 X，理由：…

## 后果（Consequences）
- 正面：…
- 负面：…
- 跟进事项：[ ] …
```

### Step 3 · 维护决策序列
- 若新决策取代旧决策：把旧 ADR 状态改为 `superseded by NNNN`
- 若目录存在 `docs/adr/README.md` 或索引文件，同步更新索引表

### Step 4 · 检索历史决策
用户问"以前为什么用 X"时：在 docs/adr/ 中按关键词搜索，引用对应 ADR 编号与结论原文，不要凭记忆回答。

## 红线
- 不虚构团队没确认过的理由；理由空缺就标"待补充"
- 一个 ADR 只记录一个决策，不要合并多个决策
