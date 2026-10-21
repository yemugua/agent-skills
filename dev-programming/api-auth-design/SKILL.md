---
slug: api-auth-design
name: API 鉴权方案设计
displayName: "API 鉴权方案设计"
description: API 鉴权方案设计：调用方（用户端/服务端/第三方/开放平台）与信任边界。
version: 1.0.0
category: dev-programming
---

# API 鉴权方案设计

## 触发场景
当用户的需求涉及：场景分析；方案选型；实现要点；防护 时使用本技能。

### Step 1 · 场景分析
调用方（用户端/服务端/第三方/开放平台）与信任边界。

### Step 2 · 方案选型
API Key（服务间简单场景）/ OAuth2.0（用户授权）/ JWT（无状态会话）/ mTLS（高安全内网），给对比表与推荐。

### Step 3 · 实现要点
密钥生成强度、存储（KMS/环境变量）、传输（仅 HTTPS）、轮换周期与双钥并行、scope 最小化。

### Step 4 · 防护
限流按 key、异常调用告警、吊销流程。

## 红线
- 密钥禁止入库明文/前端下发/写日志
- 第三方接入必须 scope 最小化
