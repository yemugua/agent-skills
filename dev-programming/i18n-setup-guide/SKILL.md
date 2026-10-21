---
slug: i18n-setup-guide
name: 国际化 i18n 搭建
displayName: "国际化 i18n 搭建"
description: 国际化 i18n 搭建：按技术栈选库（react-i18next/vue-i18n/next-intl/ICU），说明取舍。
version: 1.0.0
category: dev-programming
---

# 国际化 i18n 搭建

## 触发场景
当用户的需求涉及：选型；文案抽取；基础设施；质量保障 时使用本技能。

### Step 1 · 选型
按技术栈选库（react-i18next/vue-i18n/next-intl/ICU），说明取舍。

### Step 2 · 文案抽取
扫描代码内硬编码文案，迁移到 locale 文件，制定 key 命名规范（模块.页面.元素）。

### Step 3 · 基础设施
占位符与复数规则（ICU MessageFormat）、日期数字本地化、RTL 预留、语言切换与回退链。

### Step 4 · 质量保障
伪本地化测试找出漏翻与溢出、文案长度预留、翻译流程对接。

## 红线
- key 禁止用译文当命名
- 金额日期必须本地化，不硬编码格式
