---
name: spc-control-chart
slug: spc-control-chart-tianbao
displayName: SPC 统计过程控制
version: 1.0.0
summary: 依据 SPC 原理与 GB/T 4091，生成统计过程控制清单：控制图选择、判异准则、过程能力 CPK/PPK 分析与异常处置。
description: 当需要做SPC、统计过程控制、控制图、Xbar-R、I-MR、过程能力、CPK、PPK、判异准则时调用。输出选图、判异与能力分析。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, SPC, 统计过程控制, 控制图, 过程能力, CPK, PPK]
language: zh-CN
visibility: public
---

# SPC 统计过程控制（spc-control-chart）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据 SPC 原理与 GB/T 4091，生成统计过程控制清单：控制图选择、判异准则、过程能力 CPK/PPK 分析与异常处置。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- SPC
- 统计过程控制
- 控制图
- 过程能力
- CPK
- PPK
- 判异准则

## 三、工作流
1. 选择控制图类型（Xbar-R/I-MR/P）
2. 应用判异准则（如8条西格玛准则）
3. 计算过程能力 CPK/PPK
4. 评价过程稳定性与能力
5. 异常处置与持续改进

## 四、核心内容（检查清单与判定）
GB/T 4091 规定常规控制图的使用；过程能力以 CPK/PPK 表征，通常要求 CPK≥1.33；判异准则用于识别特殊原因波动。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未选控制图类型（Xbar-R/I-MR/P） | 选图 |
| Q2 | WARN | 未含判异准则（如8条西格玛准则） | 判异 |
| Q3 | FAIL | 未计算过程能力 CPK/PPK | 能力 |
| Q4 | WARN | 未含异常处理与改进 | 处置 |

> 脚本 `spc-control-chart_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python spc-control-chart_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python spc-control-chart_check.py --selftest
```
退出码 0=通过，1=存在 FAIL 或自检未过。

## 六、人工确认事项
- 法规条款以最新发布版本为准，标准更新后须复核本清单依据。
- 重大隐患/高风险判定需由具备资质人员签字确认。
- 涉及行政处罚或争议时，以主管部门认定为准。

## 七、输出结构
- 核查结论（通过/存在不符合项）
- 不符合项明细（编号/等级/条款/说明）
- 整改建议与闭环时限
- 留痕记录（谁/何时/依据）

## 八、常见坑
- 把"建议"当"强制"，混淆规范性条文与推荐性条文。
- 漏查时效性：证书、检测报告、许可证均有时效，过期即不符。
- 只看有无、不看有效性（如制度上墙但从未演练）。
- 样本数据造假：自检用随机样本，不等于真实合规。

## 九、免责声明
本技能为辅助参考工具，输出不构成法律/行政意见。最终合规责任由使用单位与责任人承担。引用标准以官方发布为准。

## 十、许可
Apache-2.0。可二次创作，须保留作者与出处，不得用于违法用途。

## 十一、配套资源
- `rules/规则库.md`：上述清单展开的执行细则
- `templates/模板.md`：可直接落地的记录/报告模板
- `scripts/spc-control-chart_check.py`：命令行自检脚本（带 --selftest）
