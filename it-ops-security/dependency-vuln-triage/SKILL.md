---
slug: dependency-vuln-triage
name: 依赖漏洞升级排期
displayName: "依赖漏洞升级排期"
description: 依赖漏洞升级排期：用 npm audit/pip-audit/osv-scanner 等扫描，输出漏洞清单（CVE、CVSS、影响包、修复版本）。
version: 1.0.0
category: it-ops-security
---

# 依赖漏洞升级排期

## 触发场景
当用户的需求涉及：扫描汇总；分级；升级评估；排期输出 时使用本技能。

### Step 1 · 扫描汇总
用 npm audit/pip-audit/osv-scanner 等扫描，输出漏洞清单（CVE、CVSS、影响包、修复版本）。

### Step 2 · 分级
按可利用性+暴露面分级：P0 立即修（RCE/有 EXP）、P1 一周内、P2 排期。

### Step 3 · 升级评估
每个修复版本查 breaking changes，给出兼容性矩阵与回归测试范围。

### Step 4 · 排期输出
升级排期表 + 无法升级时的缓解措施（WAF 规则、禁用功能路径）。

## 红线
- P0 漏洞不允许只排期不缓解
- 升级前必须确认有回滚方案
