---
name: customer-specific-requirements
slug: customer-specific-requirements-tianbao
displayName: 顾客特殊要求管理
version: 1.0.0
summary: 依据 IATF 16949 顾客特殊要求（CSR）管理要求，生成清单：CSR 识别与清单建立、与体系条款映射、转化到内部文件与过程、培训与执行确认、审核准备与更新跟踪。
description: 当需要做顾客特殊要求、CSR、客户特殊要求、IATF顾客要求、CSR清单、客户标准时调用。输出CSR管理清单。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, 顾客特殊要求, CSR, IATF 16949, 客户标准, 条款映射]
language: zh-CN
visibility: public
---

# 顾客特殊要求管理（customer-specific-requirements）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据 IATF 16949 顾客特殊要求（CSR）管理要求，生成清单：CSR 识别与清单建立、与体系条款映射、转化到内部文件与过程、培训与执行确认、审核准备与更新跟踪。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 顾客特殊要求
- CSR
- 客户特殊要求
- IATF顾客要求
- CSR清单

## 三、工作流
1. 识别顾客特殊要求并建立清单
2. 与体系条款做映射
3. 转化到内部文件与过程
4. 开展培训并确认执行
5. 准备审核并跟踪更新

## 四、核心内容（检查清单与判定）
顾客特殊要求（CSR）是 IATF 16949 体系的一部分，须识别、纳入体系并转化执行；遗漏 CSR 是审核常见不符合项。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未含CSR识别与清单 | 识别 |
| Q2 | FAIL | 未含与体系条款映射 | 映射 |
| Q3 | WARN | 未含转化到内部文件过程 | 转化 |
| Q4 | FAIL | 未含培训与执行确认 | 培训 |
| Q5 | WARN | 未含审核准备与更新跟踪 | 更新 |

> 脚本 `customer-specific-requirements_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python customer-specific-requirements_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python customer-specific-requirements_check.py --selftest
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
- `scripts/customer-specific-requirements_check.py`：命令行自检脚本（带 --selftest）
