---
name: process-safety
slug: process-safety-tianbao
displayName: 工艺安全管理 PSM
version: 1.0.0
summary: 依据《化工企业工艺安全管理实施导则》AQ/T 3034，生成工艺安全管理清单：工艺安全信息(PSI)、PHA  hazard 分析、操作规程、变更管理(MOC)、机械完整性、作业许可、应急响应。
description: 当需要做工艺安全、PSM、过程安全、化工工艺安全、PHA、变更管理MOC、机械完整性时调用。输出 PSM 要素清单。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [EHS, 工艺安全, PSM, AQ/T 3034, PHA, 变更管理]
language: zh-CN
visibility: public
---

# 工艺安全管理 PSM（process-safety）

> 领域：EHS ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据《化工企业工艺安全管理实施导则》AQ/T 3034，生成工艺安全管理清单：工艺安全信息(PSI)、PHA  hazard 分析、操作规程、变更管理(MOC)、机械完整性、作业许可、应急响应。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 工艺安全
- PSM
- 过程安全
- 化工工艺安全
- 变更管理MOC

## 三、工作流
1. 收集工艺安全信息(PSI)
2. 开展工艺危害分析(PHA)
3. 建立操作规程与培训
4. 实施变更管理(MOC)与机械完整性
5. 作业许可与应急响应衔接

## 四、核心内容（检查清单与判定）
AQ/T 3034 规定工艺安全管理的要素体系；PSM 聚焦高危工艺的全生命周期风险，强调 PHA、MOC、机械完整性与应急衔接。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未含工艺安全信息PSI | PSI |
| Q2 | FAIL | 未含工艺危害分析PHA | PHA |
| Q3 | WARN | 未含变更管理MOC | MOC |
| Q4 | FAIL | 未含机械完整性 | 完整性 |
| Q5 | WARN | 未含作业许可与应急 | 应急 |

> 脚本 `process-safety_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python process-safety_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python process-safety_check.py --selftest
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
- `scripts/process-safety_check.py`：命令行自检脚本（带 --selftest）
