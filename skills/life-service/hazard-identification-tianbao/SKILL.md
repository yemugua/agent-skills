---
name: hazard-identification
slug: hazard-identification-tianbao
displayName: 危险源辨识与风险评价
version: 1.0.0
summary: 依据ISO 45001:2018 条款6.1.2与GB/T 13861，生成危险源辨识与风险评价（LEC/风险矩阵）清单，输出重大危险源与控制措施。
description: 当需要做危险源辨识、风险评价、LEC法、风险矩阵、危险源清单、Job Hazard Analysis时调用。输出辨识表、风险分级与管控层级。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [质量, 危险源辨识, 风险评价, LEC, 风险矩阵, GB/T 13861, 职业健康安全]
language: zh-CN
visibility: public
---

# 危险源辨识与风险评价（hazard-identification）

> 领域：质量 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据ISO 45001:2018 条款6.1.2与GB/T 13861，生成危险源辨识与风险评价（LEC/风险矩阵）清单，输出重大危险源与控制措施。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 危险源辨识
- 风险评价
- LEC法
- 风险矩阵
- 危险源清单
- JHA

## 三、工作流
1. 划分作业活动与场所
2. 辨识根源/状态危险源（GB/T 13861）
3. 评价风险（LEC或矩阵）
4. 划分风险等级（重大/较大/一般/低）
5. 制定控制措施（消除-替代-工程-管理-PPE）

## 四、核心内容（检查清单与判定）
GB/T 13861 将危险源分为根源（能量/物质）与状态（物/人/环境/管理）；风险评价常用LEC=D×L×E×C或5×5矩阵。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未划分作业活动/场所 | 45001 6.1.2 |
| Q2 | FAIL | 未区分根源与状态危险源 | GB/T 13861 |
| Q3 | WARN | 无风险评价方法/分值 | LEC/矩阵 |
| Q4 | FAIL | 未划分风险等级 | 分级 |
| Q5 | FAIL | 无控制措施或层级错误 | 层级 |

> 脚本 `hazard-identification_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python hazard-identification_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python hazard-identification_check.py --selftest
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
- `scripts/hazard-identification_check.py`：命令行自检脚本（带 --selftest）
