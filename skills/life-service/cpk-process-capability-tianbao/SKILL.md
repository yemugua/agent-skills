---
name: cpk-process-capability
slug: cpk-process-capability-tianbao
displayName: 过程能力指数 Cpk
version: 1.0.0
summary: 依据 SPC 与过程能力分析，生成 Cpk 应用清单：数据正态性检验、Cp/Cpk 计算、规格上下限、过程能力判定（≥1.33 合格）、改进方向。
description: 当需要做过程能力、Cpk、Cp、过程能力指数、规格限、SPC能力分析时调用。输出计算与判定步骤。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, 过程能力, Cpk, Cp, 规格限, SPC]
language: zh-CN
visibility: public
---

# 过程能力指数 Cpk（cpk-process-capability）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据 SPC 与过程能力分析，生成 Cpk 应用清单：数据正态性检验、Cp/Cpk 计算、规格上下限、过程能力判定（≥1.33 合格）、改进方向。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 过程能力
- Cpk
- Cp
- 过程能力指数
- 规格限

## 三、工作流
1. 收集计量数据并检验正态性
2. 确定规格上限/下限
3. 计算 Cp 与 Cpk
4. 按判据评价（Cpk≥1.33合格）
5. 针对中心偏移/离散过大改进

## 四、核心内容（检查清单与判定）
Cp 反映过程潜力，Cpk 同时考虑中心偏移；一般要求 Cpk≥1.33，低于1.0表示能力不足需改进。计算前提是数据稳定且近似正态。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未含正态性检验/数据稳定 | 正态 |
| Q2 | FAIL | 未含 Cp/Cpk 计算 | 计算 |
| Q3 | FAIL | 未含规格上下限 | 规格 |
| Q4 | WARN | 未含能力判据（≥1.33） | 判据 |
| Q5 | WARN | 未含改进方向 | 改进 |

> 脚本 `cpk-process-capability_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python cpk-process-capability_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python cpk-process-capability_check.py --selftest
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
- `scripts/cpk-process-capability_check.py`：命令行自检脚本（带 --selftest）
