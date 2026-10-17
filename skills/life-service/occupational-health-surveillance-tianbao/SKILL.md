---
name: occupational-health-surveillance
slug: occupational-health-surveillance-tianbao
displayName: 职业健康监护
version: 1.0.0
summary: 依据《职业健康监护技术规范》GBZ 188，生成清单：危害岗位识别与监护项目、上岗前/在岗/离岗体检周期、体检机构与项目完整性、结果告知与禁忌证处理、监护档案管理。
description: 当需要做职业健康监护、职业健康体检、上岗前体检、在岗体检、离岗体检、GBZ 188时调用。输出监护管理清单。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [EHS, 职业健康监护, GBZ 188, 上岗前体检, 在岗体检, 离岗体检]
language: zh-CN
visibility: public
---

# 职业健康监护（occupational-health-surveillance）

> 领域：EHS ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据《职业健康监护技术规范》GBZ 188，生成清单：危害岗位识别与监护项目、上岗前/在岗/离岗体检周期、体检机构与项目完整性、结果告知与禁忌证处理、监护档案管理。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- 职业健康监护
- 职业健康体检
- 上岗前体检
- 在岗体检
- 离岗体检

## 三、工作流
1. 识别危害岗位与监护项目
2. 明确上岗前/在岗/离岗体检周期
3. 选择体检机构并核对项目
4. 告知结果并处理禁忌证
5. 建立并保存监护档案

## 四、核心内容（检查清单与判定）
GBZ 188 按危害因素规定监护项目与周期；上岗前发现职业禁忌证、在岗按期监护、离岗时体检，结果须告知并建档。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未含危害岗位与监护项目 | 岗位 |
| Q2 | FAIL | 未含上岗前/在岗/离岗周期 | 周期 |
| Q3 | WARN | 未含体检机构与项目完整性 | 机构 |
| Q4 | FAIL | 未含结果告知与禁忌证处理 | 告知 |
| Q5 | WARN | 未含监护档案管理 | 档案 |

> 脚本 `occupational-health-surveillance_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python occupational-health-surveillance_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python occupational-health-surveillance_check.py --selftest
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
- `scripts/occupational-health-surveillance_check.py`：命令行自检脚本（带 --selftest）
