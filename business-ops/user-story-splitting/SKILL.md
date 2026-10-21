---
slug: user-story-splitting
name: 用户故事 INVEST 拆分
displayName: "用户故事 INVEST 拆分"
description: 用户故事 INVEST 拆分：明确业务目标、用户角色、端到端主流程。
version: 1.0.0
category: business-ops
---

# 用户故事 INVEST 拆分

## 触发场景
当用户的需求涉及：理解史诗；按模式拆分；INVEST 检验；补验收标准 时使用本技能。

### Step 1 · 理解史诗
明确业务目标、用户角色、端到端主流程。

### Step 2 · 按模式拆分
工作流步骤/业务规则变体/数据变体/接口层等模式逐一切，保持每个故事可独立交付。

### Step 3 · INVEST 检验
逐条核对：独立、可协商、有价值、可估算、够小、可测试；不达标继续拆。

### Step 4 · 补验收标准
每个故事写 Gherkin 场景（Given/When/Then）与依赖关系图。

## 红线
- 故事必须对用户有价值，禁止『开发者完成XX』式故事
- 拆到 2~3 天内可完成为止
