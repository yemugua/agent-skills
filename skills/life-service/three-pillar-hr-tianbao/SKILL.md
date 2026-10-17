---
name: three-pillar-hr
slug: three-pillar-hr-tianbao
displayName: 人力资源三支柱
version: 1.0.0
summary: 依据 HR 三支柱（COE/SSC/HRBP）模型，生成清单：三角色定位与职责划分、COE 政策与专业设计、SSC 事务标准化与效率、HRBP 业务嵌入与诊断、协同机制与转型路径。
description: 当需要做HR三支柱、COE、SSC、HRBP、人力资源转型、三支柱模型时调用。输出三支柱建设清单。
license: Apache-2.0
author: 刘天宝｜墨燊
category: professional
subCategories: pro-risk-control
icon: icon.svg
tags: [招聘, HR三支柱, COE, SSC, HRBP, 人力资源转型]
language: zh-CN
visibility: public
---

# 人力资源三支柱（three-pillar-hr）

> 领域：招聘 ｜ 作者：刘天宝｜墨燊 ｜ House Style 合规技能

## 一、硬边界（什么场合用 / 不碰）
**使用场景**：依据 HR 三支柱（COE/SSC/HRBP）模型，生成清单：三角色定位与职责划分、COE 政策与专业设计、SSC 事务标准化与效率、HRBP 业务嵌入与诊断、协同机制与转型路径。
**不适用**：非本行的通用咨询、法律诉讼代理、与现行规范冲突的诉求。所有结论须以**现行有效**法规/标准为准，本技能不做最终合规裁定。

## 二、使用场景（触发词）
- HR三支柱
- COE
- SSC
- HRBP
- 人力资源转型

## 三、工作流
1. 定位三角色并划分职责
2. 由COE负责政策与专业设计
3. 由SSC实现事务标准化提效
4. 由HRBP嵌入业务做诊断
5. 建立协同机制与转型路径

## 四、核心内容（检查清单与判定）
三支柱把 HR 分为专家中心（COE）、共享服务（SSC）与业务伙伴（HRBP），通过分工协同提升专业性与响应速度。

| 编号 | 等级 | 检查项 | 依据 |
|---|---|---|---|
| Q1 | FAIL | 未含三角色定位与职责划分 | 定位 |
| Q2 | FAIL | 未含COE政策与专业设计 | COE |
| Q3 | WARN | 未含SSC事务标准化 | SSC |
| Q4 | FAIL | 未含HRBP业务嵌入与诊断 | HRBP |
| Q5 | WARN | 未含协同机制与转型路径 | 协同 |

> 脚本 `three-pillar-hr_check.py` 可对上述清单做自检：传入 JSON 记录，输出 FAIL/WARN 与命中条款。

## 五、脚本用法
```bash
# 对单条记录核查
python three-pillar-hr_check.py --file record.json --today 2026-10-13
# 自检（内置 good/bad 样本断言）
python three-pillar-hr_check.py --selftest
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
- `scripts/three-pillar-hr_check.py`：命令行自检脚本（带 --selftest）
