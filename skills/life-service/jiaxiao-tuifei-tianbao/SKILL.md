---
name: jiaxiao-tuifei
slug: jiaxiao-tuifei-tianbao
displayName: 驾校退费 驾校报名费退款 驾校培训费退费 学车退学退费 驾考退费维权 12328投诉 驾校退费流程 驾校不退费怎么办
display_name: "驾校退费 驾校报名费退款 驾校培训费退费 学车退学退费 驾考退费维权 12328投诉 驾校退费流程 驾校不退费怎么办"
display_name_en: "Driving School Tuition Refund and Rights Protection"
version: "1.0.0"
summary: 按培训进度算清驾校该退你多少钱，并生成退费申请书、投诉话术与维权路径。
description: 面向驾校学员与家属的退费维权技能。当用户说「驾校不退费怎么办」「报名了不想学了能退多少钱」「驾校报名费能退吗」「科目一过了退学扣多少」「驾校拖延不给安排练车想退钱」「驾校合同写概不退费有效吗」「退学申请书怎么写」「投诉驾校打哪个电话」时使用。技能会按未开训/已过科一/已上实操等阶段核算应退金额区间（保守/合理/争取），识别「概不退费」等无效格式条款与驾校违约情形，输出退费申请书、材料清单、12328/12315/12345 投诉要点与小额诉讼路径。仅提供规则与文书，不代理案件、不承诺结果。
license: Apache-2.0
author: 刘天宝｜墨燊
category: life-service
subCategories:
  - consumer-rights
icon: icon.svg
tags: [驾校退费, 驾校报名费, 培训费退费, 退学退费, 驾考维权, 12328, 12315, 格式条款, 退费申请书, 消费维权]
language: zh-CN
visibility: public
---

# 驾校退费｜报名费培训费退款核算与维权

## 一、硬边界

| 能做 | 不能做 |
|---|---|
| 按培训进度核算应退金额区间（保守/合理/争取三档） | 不能替你向法院/12328 提交申请或代签文书 |
| 判定培训阶段（未开训 / 已开理论 / 已上实操 / 已考完） | 不能查到某家驾校的真实收费明细，只能按你提供的数字算 |
| 识别「概不退费」「一经报名概不退还」等无效格式条款 | 不能保证一定退到钱，实际结果取决于证据与协商 |
| 识别驾校违约情形（超期不安排练车、与承诺不符等） | 不能给出诉讼胜诉率、不能预测判决金额 |
| 生成退费申请书、证据清单、投诉话术 | 不能代收代管款项、不能提供律师执业意见 |
| 给出主管部门投诉路径与时效提示 | 不处理驾照考试作弊、买卖驾照等违法事项 |

金额全部是**估算区间**，不是法律意见。最终以合同约定、票据、当地主管部门处理意见或法院认定为准。

## 二、什么时候用

| 用户说法 | 用不用 |
|---|---|
| 驾校不退费怎么办 / 驾校扣我一千多合理吗 | 用，直接走核算流程 |
| 报名了不想学了，能退多少钱 | 用 |
| 科目一考过了想退学，扣多少 | 用 |
| 驾校拖了三个月没给我安排练车 | 用，按驾校违约处理 |
| 合同上写着概不退费，是不是就没办法了 | 用，该条款属无效格式条款 |
| 驾校搬迁/教练辱骂/承诺包过没兑现 | 用 |
| 我想考驾照，推荐个驾校 | 不用，本技能只处理退费 |
| 科二挂了五次怎么办 | 不用 |
| 我的驾照扣分了怎么查 | 不用 |

## 三、完整工作流

1. **收齐六个关键数字**：合同总额、已缴金额、报名日期、申请退费日期、已通过科目、已完成学时（驾校 APP/IC 卡计时记录可导出）。没有学时记录时，脚本按已通过科目推定学时。
2. **固定扣减项先摆出来**：建档受理费、教材资料费、体检照相费、已代缴的考试费。这些是「已经实际花掉的」，退费时一般不退。
3. **算已消耗培训费**：培训费 = 合同总额 − 固定成本；学时单价 = 培训费 ÷ 62（C1 教学大纲总学时，C2 为 60）；已消耗 = 已完成学时 × 单价。
4. **判断谁违约**：
   - 驾校方违约（超 60 日不安排培训、擅自搬迁、虚假承诺、教练殴打辱骂）→ 学员可主张**全额退还**并索赔，违约金为 0。
   - 学员方原因退学 → 驾校只能扣「已实际发生的费用 + 合理违约金」，违约金以合同约定为准，但**超过实际损失 30% 可主张过分高于损失**。
5. **校验合同里的霸王条款**：`概不退费`、`一经报名概不退款`、`最终解释权归本驾校` 均属免除自身责任、排除对方主要权利的**格式条款，依法无效**（民法典第 496、497 条）。
6. **生成文书**：退费申请书（含事实、依据、诉求金额、期限）、证据清单、投诉话术。
7. **按阶梯维权**：协商 → 12328（交通运输服务监督热线，驾校主管部门）→ 12315（市场监管，价格与格式条款）→ 12345 → 人民法院小额诉讼（三年诉讼时效，民法典第 188 条）。
8. **留痕**：所有沟通用文字（微信/短信），电话后补一条确认短信；现场缴费要发票或盖章收据，转账要备注。

## 四、脚本用法

```powershell
# 自检（3 个内置样例断言）
& "C:\Users\Ti'an'bao\.workbuddy\binaries\python\versions\3.13.12\python.exe" "scripts\tuifei_calc.py" --selftest

# 实际核算（输入 JSON 档案，输出报告与退费申请书）
& "C:\Users\Ti'an'bao\.workbuddy\binaries\python\versions\3.13.12\python.exe" "scripts\tuifei_calc.py" --file case.json --out out
```

| 参数 | 说明 |
|---|---|
| `--file` | 学员档案 JSON 路径，见下方字段表 |
| `--out` | 输出目录（默认 `out`），生成 `退费核算报告.md`、`退费申请书.md`、`证据清单.md` |
| `--selftest` | 运行内置样例自检，结果同时写入 `scripts/_selftest_result.txt` |

输入 JSON 字段（缺失字段用默认值）：

| 字段 | 类型 | 默认 | 说明 |
|---|---|---|---|
| `学员姓名` | str | 学员 | 用于文书抬头 |
| `驾校名称` | str | 驾校 | |
| `合同总额` | float | 4800 | 报名合同约定总额 |
| `已缴金额` | float | 同合同总额 | 实际已付 |
| `报名日期` | str(YYYY-MM-DD) | 90 天前 | |
| `申请退费日期` | str(YYYY-MM-DD) | 今天 | |
| `是否建档受理` | bool | false | 是否已建档、发教材 |
| `已通过科目` | list | [] | `科目一`/`科目二`/`科目三`/`科目四` |
| `已完成学时` | dict | {} | 如 `{"科目二": 6}` |
| `已代缴考试费` | float | 0 | 已实付给车管所的考试费 |
| `合同约定违约金比例` | float | 0 | 0.2 表示 20% |
| `驾校违约情形` | str | 无 | 填「超期未安排练车」等 |
| `驾校超期未安排天数` | int | 0 | ≥60 视为驾校违约 |
| `是否有概不退费条款` | bool | false | |
| `是否有书面合同` | bool | true | |
| `是否开具发票` | bool | false | |
| `车型` | str | C1 | C1/C2，影响总学时 |

## 五、规则与要件库

生成任何文书前，**先读这两个文件**：

- `rules/tuifei-rules.md` —— 扣减项口径、三档金额算法、违约与格式条款认定、各地常见扣费区间、投诉与时效依据。
- `templates/tuifei-application.md` —— 退费申请书模板与填空说明。

脚本里的常量与这两份文件保持一致；若你修改规则文件，同步修改脚本顶部常量。

## 六、最常见的坑

1. **把「已缴金额」和「合同总额」混为一谈**。很多驾校分期、先交定金再补尾款，只按合同总额算会高估退款，必须按**已实缴**算。
2. **学时记录没有导出就空口谈**。驾校常按「已学完整个科目」扣费，而学时系统里往往只刷了几个学时。**务必导出计时记录截图**（驾校 APP / 各省驾驶培训监管平台），这是砍掉不合理扣费最有力的一张牌。
3. **轻信「概不退费」就放弃**。该条款是无效格式条款；但当驾校拿出**你签字确认的、明确列明扣费标准的**退费约定时，法院通常会尊重约定，所以要区分「霸王条款」和「明示的扣费标准」。
4. **没有发票或收据就投诉**。12328/12315 受理要基本凭证，转账记录必须能显示收款方为驾校或其法定代表人；现金缴费又无收据时，先补一个盖章的缴费证明再去投诉。
5. **口头协商不留痕**。电话里说好退 3000，回头驾校只认 1000。**所有协商结论落到文字**，并明确「几月几日前退到指定账户」。
6. **违约金按合同全额认**。合同约定 30%、50% 不代表有效；违约金以**实际损失**为基准，超过损失 30% 可请求调减（民法典第 585 条及相关司法解释）。
7. **超时效**。普通民事纠纷诉讼时效三年（民法典第 188 条），从知道权利受损日起算；久拖不决也别拖过三年。
8. **投诉渠道找错**。驾校的主管是**交通运输部门**（12328），不是教育局；价格欺诈、虚假宣传、格式条款归**市场监管**（12315）；两条线可以同时走。

## 七、边界与免责

- 本技能输出的是**规则推演与文书模板**，不构成法律意见，也不构成任何退费结果的承诺。
- 各省、市对驾校退费的具体规定（如部分地区有「未开训扣 5%」「开训后按学时」等地方法规或行业规范）可能与本技能默认口径不同，以当地主管部门解释为准。
- 涉及金额较大（一般 2 万元以上）、存在人身伤害或群体性纠纷时，建议咨询当地律师或法律援助机构（12348 公共法律服务热线）。
- 不协助虚构事实、伪造学时记录或发票。

## 八、许可

本项目采用 Apache License 2.0 许可，正文如下：

```
                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/

   TERMS AND CONDITIONS FOR USE, REPRODUCTION, AND DISTRIBUTION

   1. Definitions.

      "License" shall mean the terms and conditions for use, reproduction,
      and distribution as defined by Sections 1 through 9 of this document.

      "Licensor" shall mean the copyright owner or entity authorized by
      the copyright owner that is granting the License.

      "Legal Entity" shall mean the union of the acting entity and all
      other entities that control, are controlled by, or are under common
      control with that entity. For the purposes of this definition,
      "control" means (i) the power, direct or indirect, to cause the
      direction or management of such entity, whether by contract or
      otherwise, or (ii) ownership of fifty percent (50%) or more of the
      outstanding shares, or (iii) beneficial ownership of such entity.

      "You" (or "Your") shall mean an individual or Legal Entity
      exercising permissions granted by this License.

      "Source" form shall mean the preferred form for making modifications,
      including but not limited to software source code, documentation
      source, and configuration files.

      "Object" form shall mean any form resulting from mechanical
      transformation or translation of a Source form, including but
      not limited to compiled object code, generated documentation,
      and conversions to other media types.

      "Work" shall mean the work of authorship, whether in Source or
      Object form, made available under the License, as indicated by a
      copyright notice that is included in or attached to the work.

      "Derivative Works" shall mean any work, whether in Source or Object
      form, that is based on (or derived from) the Work and for which the
      editorial revisions, annotations, elaborations, or other modifications
      represent, as a whole, an original work of authorship.

      "Contribution" shall mean any work of authorship, including
      the original version of the Work and any modifications or additions
      to that Work or Derivative Works thereof, that is intentionally
      submitted to Licensor for inclusion in the Work by the copyright owner
      or by an individual or Legal Entity authorized to submit on behalf of
      the copyright owner.

      "Contributor" shall mean Licensor and any individual or Legal Entity
      on behalf of whom a Contribution has been received by Licensor and
      subsequently incorporated within the Work.

   2. Grant of Copyright License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      copyright license to reproduce, prepare Derivative Works of,
      publicly display, publicly perform, sublicense, and distribute the
      Work and such Derivative Works in Source or Object form.

   3. Grant of Patent License. Subject to the terms and conditions of
      this License, each Contributor hereby grants to You a perpetual,
      worldwide, non-exclusive, no-charge, royalty-free, irrevocable
      (except as stated in this section) patent license to make, have made,
      use, offer to sell, sell, import, and otherwise transfer the Work.

   4. Redistribution. You may reproduce and distribute copies of the
      Work or Derivative Works thereof in any medium, with or without
      modifications, and in Source or Object form, provided that You
      meet the following conditions:

      (a) You must give any other recipients of the Work or
          Derivative Works a copy of this License; and

      (b) You must cause any modified files to carry prominent notices
          stating that You changed the files; and

      (c) You must retain, in the Source form of any Derivative Works
          that You distribute, all copyright, patent, trademark, and
          attribution notices from the Source form of the Work; and

      (d) If the Work includes a "NOTICE" text file as part of its
          distribution, then any Derivative Works that You distribute
          must include a readable copy of the attribution notices
          contained within such NOTICE file.

   5. Submission of Contributions. Unless You explicitly state otherwise,
      any Contribution intentionally submitted for inclusion in the Work
      by You to the Licensor shall be under the terms and conditions of
      this License, without any additional terms or conditions.

   6. Trademarks. This License does not grant permission to use the trade
      names, trademarks, service marks, or product names of the Licensor.

   7. Disclaimer of Warranty. Unless required by applicable law or
      agreed to in writing, Licensor provides the Work (and each
      Contributor provides its Contributions) on an "AS IS" BASIS,
      WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
      implied.

   8. Limitation of Liability. In no event and under no legal theory,
      whether in tort (including negligence), contract, or otherwise,
      unless required by applicable law (such as deliberate and grossly
      negligent acts) or agreed to in writing, shall any Contributor be
      liable to You for damages, including any direct, indirect, special,
      incidental, or consequential damages of any character arising as a
      result of this License or out of the use or inability to use the
      Work.

   9. Accepting Warranty or Additional Liability. While redistributing
      the Work or Derivative Works thereof, You may choose to offer,
      and charge a fee for, acceptance of support, warranty, indemnity,
      or other liability obligations and/or rights consistent with this
      License.

   END OF TERMS AND CONDITIONS
```

Copyright 2026 刘天宝｜墨燊. Licensed under the Apache License, Version 2.0.
