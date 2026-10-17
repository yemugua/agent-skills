---
name: reliability-engineering
slug: reliability-engineering-tianbao
displayName: 可靠性工程
version: 1.0.0
summary: 依据可靠性工程方法，生成可靠性清单：可靠性指标（MTBF/可用度/失效率）、建模与预计、可靠性试验（环境/寿命/加速）、FMECA 与可靠性增长、数据分析改进闭环。
description: 当需要做可靠性工程、可靠性、MTBF、可用度、失效率、可靠性试验、可靠性增长、FMECA时调用。输出指标、建模、试验与改进清单。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, 可靠性工程, 可靠性, MTBF, 可用度, 失效率, FMECA]
language: zh-CN
visibility: public
---

# 可靠性工程（reliability-engineering）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据可靠性工程方法，生成可靠性清单：可靠性指标（MTBF/可用度/失效率）、建模与预计、可靠性试验（环境/寿命/加速）、FMECA 与可靠性增长、数据分析改进闭环。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 可靠性工程
- 可靠性
- MTBF
- 可用度
- 失效率
- 可靠性试验
- 可靠性增长

## 三、工作流
1. 明确可靠性指标（MTBF/可用度/失效率）
2. 可靠性建模与预计（串联/冗余）
3. 可靠性试验（环境/寿命/加速）
4. FMECA与可靠性增长
5. 数据分析与改进闭环

## 四、核心内容（检查清单与判定）
可靠性工程以 MTBF、可用度、失效率等指标衡量产品持续工作能力；通过可靠性试验与 FMECA 识别薄弱环节，以增长试验驱动改进。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未明确可靠性指标（MTBF/可用度/失效率） | 指标 |
| Q2 | WARN | 未含可靠性建模/预计（串联/冗余） | 建模 |
| Q3 | FAIL | 未含可靠性试验（环境/寿命/加速） | 试验 |
| Q4 | WARN | 未含FMECA/可靠性增长 | 增长 |
| Q5 | FAIL | 未含数据分析与改进闭环 | 改进 |

> 脚本 `reliability-engineering_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python reliability-engineering_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python reliability-engineering_check.py --selftest
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
- `scripts/reliability-engineering_check.py`：命令行自检脚本（带 --selftest）
