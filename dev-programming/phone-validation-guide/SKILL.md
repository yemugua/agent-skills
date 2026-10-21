---
slug: phone-validation-guide
name: 手机号验证规范
displayName: "手机号验证规范"
description: 手机号验证规范：E.164 存储、libphonenumber 校验，国内 11 位与海外号段处理。
version: 1.0.0
category: dev-programming
---

# 手机号验证规范

## 触发场景
当用户的需求涉及：格式校验；防刷设计；存储与展示 时使用本技能。

### Step 1 · 格式校验
E.164 存储、libphonenumber 校验，国内 11 位与海外号段处理。

### Step 2 · 防刷设计
验证码：发送频控（按号/IP/设备）、图形验证前置、有效期与尝试次数限制、通道费预警。

### Step 3 · 存储与展示
加密或脱敏存储要求、日志不落全号、展示 138****1234。

## 红线
- 验证码禁止写入日志或返回给前端
- 频控必须有，防短信轰炸
