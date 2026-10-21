---
slug: money-precision-guide
name: 金额精度处理
displayName: "金额精度处理"
description: 金额精度处理：整数最小单位（分）或 DECIMAL，禁止 float/double 存金额；数据库字段类型与精度。
version: 1.0.0
category: dev-programming
---

# 金额精度处理

## 触发场景
当用户的需求涉及：存储规范；计算规范；展示规范；对账校验 时使用本技能。

### Step 1 · 存储规范
整数最小单位（分）或 DECIMAL，禁止 float/double 存金额；数据库字段类型与精度。

### Step 2 · 计算规范
十进制库运算、舍入规则统一（银行家舍入或四舍五入，明确一种）、分摊用尾差归尾法。

### Step 3 · 展示规范
格式化（千分位、币种符号）与展示精度分离；接口返回保持精度。

### Step 4 · 对账校验
汇总金额=明细之和的断言与对账任务。

## 红线
- 禁止 float 存算金额
- 舍入规则全局统一，禁止各处自定义
