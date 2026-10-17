---
name: fmea
slug: fmea-tianbao
displayName: FMEA 失效模式与影响分析
version: 1.0.0
summary: 依据 AIAG-VDA FMEA 手册，生成 FMEA 清单：结构/功能/失效三层分析、S/O/D 评级、AP 动作优先级与措施闭环。
description: 当需要做FMEA、失效模式分析、PFMEA、DFMEA、AP优先级、潜在失效、风险分析时调用。输出七步法结构、评级与措施。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, FMEA, PFMEA, DFMEA, 失效模式, AP优先级, 风险分析]
language: zh-CN
visibility: public
---

# FMEA 失效模式与影响分析（fmea）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据 AIAG-VDA FMEA 手册，生成 FMEA 清单：结构/功能/失效三层分析、S/O/D 评级、AP 动作优先级与措施闭环。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- FMEA
- 失效模式
- PFMEA
- DFMEA
- AP优先级
- 潜在失效
- 风险分析

## 三、工作流
1. 结构/功能/失效三层分析
2. 识别失效原因与后果
3. 评级严重度/频度/探测度（S/O/D）
4. 用 AP 动作优先级替代 RPN
5. 措施闭环与再评估

## 四、核心内容（检查清单与判定）
AIAG-VDA FMEA 采用七步法，以结构-功能-失效分析为基础，用 AP（Action Priority）高/中/低替代传统 RPN 排定措施优先级。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未做结构/功能/失效三层分析 | 七步法 |
| Q2 | WARN | 未评严重度/频度/探测度(S/O/D) | 评级 |
| Q3 | FAIL | 未用AP(动作优先级)替代RPN | AP |
| Q4 | WARN | 未含措施闭环与再评估 | 闭环 |

> 脚本 `fmea_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python fmea_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python fmea_check.py --selftest
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
- `scripts/fmea_check.py`：命令行自检脚本（带 --selftest）
