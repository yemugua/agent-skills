---
slug: jwt-security-practices
name: JWT 安全实践
displayName: "JWT 安全实践"
description: JWT 安全实践：检查：算法是否固定（防 alg:none 与混合算法攻击）、密钥强度与存储、exp/iat/aud/iss 校验、刷新 token 机制、注销黑名单。
version: 1.0.0
category: dev-programming
---

# JWT 安全实践

## 触发场景
当用户的需求涉及：审查现有 JWT 实现；给出加固方案；给出代码示例 时使用本技能。

### Step 1 · 审查现有 JWT 实现
检查：算法是否固定（防 alg:none 与混合算法攻击）、密钥强度与存储、exp/iat/aud/iss 校验、刷新 token 机制、注销黑名单。

### Step 2 · 给出加固方案
输出修复清单：改用 RS256 或强密钥 HS256、access token 短有效期(≤15min)、refresh token 轮换、jti 黑名单。

### Step 3 · 给出代码示例
按用户技术栈给出签发与校验代码，包含错误处理。

## 红线
- 不要建议把敏感数据放进 payload（JWT 仅编码非加密）
- 密钥永不写入代码或日志
