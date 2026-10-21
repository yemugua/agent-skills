---
slug: api-doc-automation
name: 接口文档自动化
displayName: "接口文档自动化"
description: 接口文档自动化：OpenAPI 3.x 为单一事实源：从代码注解生成（Springdoc/DRF Spectacular 等）或手写 spec 校验。
version: 1.0.0
category: dev-programming
---

# 接口文档自动化

## 触发场景
当用户的需求涉及：规范落地；示例与校验；发布；流程 时使用本技能。

### Step 1 · 规范落地
OpenAPI 3.x 为单一事实源：从代码注解生成（Springdoc/DRF Spectacular 等）或手写 spec 校验。

### Step 2 · 示例与校验
请求/响应示例自动生成，CI 中 spec 与实现 diff 校验，破坏性变更标记。

### Step 3 · 发布
文档站点自动部署（Swagger UI/Redoc），版本化（v1/v2 并存）。

### Step 4 · 流程
接口变更 PR 必须含 spec 更新，review 时文档与实现同查。

## 红线
- 文档与实现不一致时以 CI 校验为准，禁止手工维护两份
- 破坏性变更必须先公告
